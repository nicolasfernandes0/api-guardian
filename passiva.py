import streamlit as st
import requests
import json
from zeep import Client, Settings
from zeep.exceptions import Fault
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Hub de Integrações", layout="wide")
st.title("🔄 Hub de Integrações: Ativa & Passiva")

# ==========================================
# CONFIGURAÇÃO DE INFRAESTRUTURA (SIDEBAR)
# ==========================================
st.sidebar.header("⚙️ Configurações de Conexão")
vm_ip = st.sidebar.text_input("IP Público da VM GCP", value="34.57.131.171").strip()
api_base_url = f"http://{vm_ip}:8000" if vm_ip else "http://localhost:8000"

st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Endpoints Ativos na VM")
st.sidebar.caption("Copie para configurar os seus testes.")

st.sidebar.markdown("**REST (JSON):**")
st.sidebar.code(f"{api_base_url}/api/rest/receber", language="http")

st.sidebar.markdown("**SOAP (XML):**")
st.sidebar.code(f"{api_base_url}/api/soap/receber", language="http")

st.sidebar.markdown("**LOGS (Consulta):**")
st.sidebar.code(f"{api_base_url}/api/logs", language="http")


# Criando as três abas principais do sistema
tab_http, tab_soap_wsdl, tab_monitor = st.tabs([
    "📤 Passiva (HTTP Genérico: REST / SOAP Manual)", 
    "📤 Passiva (SOAP via WSDL Toledo)", 
    "📥 Ativa (Monitor de Recebimento)"
])

# ==========================================
# ABA 1: Ativa - HTTP GENÉRICO (REST & SOAP MANUAL)
# ==========================================
with tab_http:
    st.header("Integração Ativa: Cliente HTTP Genérico")
    st.markdown("Envie requisições REST (JSON) ou monte a sua própria estrutura SOAP (XML) manualmente.")
    
    col_meth, col_url, col_type = st.columns([1, 3, 1])
    with col_meth:
        http_method = st.selectbox("Método", ["POST", "GET", "PUT", "PATCH", "DELETE"])
    with col_url:
        default_req_url = f"{api_base_url}/api/rest/receber"
        req_url = st.text_input("URL de Destino", value=default_req_url)
    with col_type:
        payload_format = st.selectbox("Formato do Payload", ["JSON (REST)", "XML (SOAP)"])
        
    st.subheader("Headers e Body")
    
    # Preenchimento dinâmico dos campos baseado no formato escolhido
    if payload_format == "JSON (REST)":
        default_headers = '{\n  "Content-Type": "application/json"\n}'
        default_body = '{\n  "mensagem": "Teste de envio REST genérico"\n}'
    else:
        default_headers = '{\n  "Content-Type": "text/xml; charset=utf-8",\n  "SOAPAction": "http://toledobrasil.com.br/WS_Guardian/SuaOperacao"\n}'
        default_body = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <SuaOperacao xmlns="http://toledobrasil.com.br/WS_Guardian">
      <Parametro>Valor</Parametro>
    </SuaOperacao>
  </soap:Body>
</soap:Envelope>"""

    col_h, col_b = st.columns(2)
    with col_h:
        st.info("⚠️ Cabeçalhos devem ser um JSON válido.")
        req_headers_str = st.text_area("Headers (JSON)", value=default_headers, height=250)
    with col_b:
        st.info(f"📝 Corpo da requisição no formato {payload_format}.")
        req_body_str = st.text_area("Body (Payload)", value=default_body, height=250)
    
    if st.button("Disparar Requisição HTTP", type="primary", use_container_width=True):
        if not req_url:
            st.warning("Por favor, insira a URL de destino.")
        else:
            try:
                headers = json.loads(req_headers_str) if req_headers_str.strip() else {}
                
                # Tratamento de URL
                if not req_url.startswith(("http://", "https://")):
                    req_url = "http://" + req_url
                
                with st.spinner("A enviar requisição..."):
                    # Se for JSON, envia como JSON. Se for XML, codifica a string e envia como Data bruta.
                    if payload_format == "JSON (REST)":
                        body = json.loads(req_body_str) if req_body_str.strip() else None
                        response = requests.request(method=http_method, url=req_url, headers=headers, json=body, verify=False)
                    else:
                        body_raw = req_body_str.encode('utf-8') if req_body_str.strip() else None
                        response = requests.request(method=http_method, url=req_url, headers=headers, data=body_raw, verify=False)
                
                st.divider()
                if response.status_code < 400:
                    st.success(f"✅ Status Code: {response.status_code}")
                else:
                    st.error(f"⚠️ Status Code: {response.status_code}")
                
                # Exibe a resposta baseado no formato recebido
                if "application/json" in response.headers.get("Content-Type", ""):
                    st.json(response.json())
                elif "text/xml" in response.headers.get("Content-Type", ""):
                    st.code(response.text, language="xml")
                else:
                    st.text(response.text)
                    
            except json.JSONDecodeError:
                st.error("Erro nos Headers: Certifique-se de que a caixa 'Headers' contém um JSON válido (use aspas duplas).")
            except Exception as e:
                st.error(f"Erro na ligação: {e}")

# ==========================================
# ABA 2: PASSIVA - ENVIAR SOAP (VIA WSDL)
# ==========================================
with tab_soap_wsdl:
    st.header("Integração Passiva: Consumo SOAP via WSDL")
    st.markdown("Esta aba lê o documento WSDL e cria a estrutura XML automaticamente.")
    
    default_wsdl = "http://services.toledobrasil.com/WS_GUARDIAN/WS_GUARDIAN_PLUS.asmx?wsdl"
    wsdl_input = st.text_input("URL do WSDL", value=default_wsdl)
    
    wsdl_url = wsdl_input.strip()
    if wsdl_url and not wsdl_url.startswith(("http://", "https://")):
        wsdl_url = "http://" + wsdl_url
        
    inferred_endpoint = wsdl_url.split("?")[0] if "?" in wsdl_url else wsdl_url

    if st.button("Carregar WSDL e Mapear Métodos", use_container_width=True):
        try:
            with st.spinner("A ler e analisar o documento WSDL..."):
                settings = Settings(strict=False, xml_huge_tree=True)
                client = Client(wsdl=wsdl_url, settings=settings)
                st.session_state.soap_client = client
                st.success("✅ Estruturas WSDL mapeadas com sucesso!")
        except Exception as e:
            st.error(f"Erro ao analisar o WSDL: {e}")

    if st.session_state.get("soap_client"):
        client = st.session_state.soap_client
        try:
            operations = list(client.service._binding._operations.keys())
            operations.sort()
        except Exception:
            operations = []
        
        st.divider()
        col_op1, col_op2 = st.columns(2)
        with col_op1:
            selected_operation = st.selectbox("Selecione a Operação", operations)
        with col_op2:
            force_endpoint = st.text_input("Forçar Endpoint de Destino", value=inferred_endpoint)
        
        def extract_skeleton(element_type, depth=0, max_depth=3):
            if depth > max_depth: return "..."
            if not element_type: return "string"
            if hasattr(element_type, 'elements'):
                return {name: extract_skeleton(el.type, depth+1, max_depth) for name, el in element_type.elements}
            return getattr(element_type, 'name', 'string')

        def dict_to_xml_str(d, indent=8):
            lines = []
            space = " " * indent
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, dict):
                        lines.append(f"{space}<{k}>")
                        lines.append(dict_to_xml_str(v, indent + 2))
                        lines.append(f"{space}</{k}>")
                    else:
                        lines.append(f"{space}<{k}>Valor_{v}</{k}>")
            return "\n".join(lines)

        tns = getattr(client.wsdl, "target_namespace", "http://toledobrasil.com.br/WS_Guardian")
        
        try:
            op = client.service._binding._operations[selected_operation]
            skeleton = {}
            if hasattr(op.input.body, 'type') and hasattr(op.input.body.type, 'elements'):
                for name, el in op.input.body.type.elements:
                    skeleton[name] = extract_skeleton(el.type)
            
            xml_inner_body = dict_to_xml_str(skeleton, indent=8)
            
            xml_template = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{selected_operation} xmlns="{tns}">
{xml_inner_body}
    </{selected_operation}>
  </soap:Body>
</soap:Envelope>"""
        except Exception as e:
            xml_template = f""
            
        st.markdown("**Envelope SOAP XML Gerado Automaticamente**")
        soap_xml_payload = st.text_area("Edite os valores das tags abaixo", value=xml_template, height=350)
        
        if st.button("Disparar Requisição SOAP (WSDL)", type="primary", use_container_width=True):
            try:
                with st.spinner(f"A disparar XML para o método {selected_operation}..."):
                    tns_clean = tns.rstrip('/')
                    soap_action = f"{tns_clean}/{selected_operation}"
                    
                    headers = {
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": soap_action
                    }
                    
                    destino_final = force_endpoint if force_endpoint else inferred_endpoint
                    
                    response = requests.post(
                        url=destino_final,
                        data=soap_xml_payload.encode('utf-8'),
                        headers=headers,
                        verify=False
                    )
                
                st.divider()
                if response.status_code == 200:
                    st.success(f"✅ Sucesso! Status Code: {response.status_code}")
                else:
                    st.error(f"⚠️ Erro do servidor. Status Code: {response.status_code}")
                
                st.markdown("**XML de Resposta Recebido:**")
                st.code(response.text, language="xml")
                
            except Exception as e:
                st.error(f"Erro Crítico de Rede: {e}")

# ==========================================
# ABA 3: ATIVA - MONITORIZAÇÃO REMOTA DA VM
# ==========================================
with tab_monitor:
    st.header("Integração Ativa: Webhooks Recebidos na VM")
    st.markdown("Consulte ou limpe o histórico de requisições que chegam ao seu servidor FastAPI.")
    
    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        atualizar = st.button("Atualizar Lista 🔄", use_container_width=True)
    with col_btn2:
        limpar = st.button("Limpar Histórico 🗑️", type="secondary", use_container_width=True)
        
    if limpar:
        try:
            url_limpar = f"{api_base_url}/api/logs/limpar"
            res_limpar = requests.delete(url_limpar, timeout=5)
            if res_limpar.status_code == 200:
                st.toast("🧹 Histórico de logs limpo com sucesso!")
            else:
                st.error("Falha ao enviar comando de limpeza para a VM.")
        except Exception as e:
            st.error(f"Erro ao tentar limpar: {e}")
            
    try:
        url_logs = f"{api_base_url}/api/logs"
        response = requests.get(url_logs, timeout=5)
            
        if response.status_code == 200:
            logs = response.json()
            
            if not logs:
                st.info("Nenhuma requisição intercetada até ao momento na sua VM.")
            else:
                for idx, log in enumerate(logs):
                    with st.expander(f"[{log['data_hora']}] Requisição {log['tipo']} Intercetada"):
                        st.markdown("**Headers Originais:**")
                        st.json(log["headers"])
                        st.markdown("**Conteúdo Recebido (Payload/Body):**")
                        if log["tipo"] == "REST":
                            st.json(log["payload"])
                        else:
                            st.code(log["payload"], language="xml")
        else:
            st.error(f"Não foi possível obter os logs. Código da API: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Não foi possível estabelecer conexão com o servidor em `{api_base_url}`.")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
