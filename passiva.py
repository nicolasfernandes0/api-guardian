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
# Configurado com o seu IP público real do GCP
vm_ip = st.sidebar.text_input("IP Público da VM GCP", value="34.57.131.171").strip()
api_base_url = f"http://{vm_ip}:8000" if vm_ip else "http://localhost:8000"

st.sidebar.markdown("---")
st.sidebar.info(f"🔗 **Endpoints ativos na sua VM:**\n"
                f"- **REST:** `{api_base_url}/api/rest/receber`\n"
                f"- **SOAP:** `{api_base_url}/api/soap/receber`\n"
                f"- **LOGS:** `{api_base_url}/api/logs`")

# Criando as três abas da arquitetura
tab_rest, tab_soap, tab_monitor = st.tabs([
    "📤 Passiva (Enviar REST)", 
    "📤 Passiva (Enviar SOAP XML)", 
    "📥 Ativa (Monitor de Recebimento)"
])

# ==========================================
# ABA 1: PASSIVA - ENVIAR REST
# ==========================================
with tab_rest:
    st.header("Integração Passiva: Consumo REST")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        http_method = st.selectbox("Método", ["GET", "POST", "PUT", "PATCH", "DELETE"])
    with col2:
        default_rest_url = f"{api_base_url}/api/rest/receber"
        rest_url = st.text_input("URL da API REST", value=default_rest_url)
        
    st.subheader("Headers e Body")
    col_h, col_b = st.columns(2)
    with col_h:
        rest_headers_str = st.text_area("Headers (JSON)", value='{\n  "Content-Type": "application/json"\n}', height=150)
    with col_b:
        rest_body_str = st.text_area("Body (JSON)", value='{\n  "mensagem": "Teste de envio REST"\n}', height=150)
    
    if st.button("Disparar Requisição REST", type="primary", use_container_width=True):
        if not rest_url:
            st.warning("Insira a URL.")
        else:
            try:
                headers = json.loads(rest_headers_str) if rest_headers_str.strip() else {}
                body = json.loads(rest_body_str) if rest_body_str.strip() else None
                
                if not rest_url.startswith(("http://", "https://")):
                    rest_url = "http://" + rest_url
                
                with st.spinner("Enviando..."):
                    response = requests.request(
                        method=http_method,
                        url=rest_url,
                        headers=headers,
                        json=body if http_method in ["POST", "PUT", "PATCH"] else None,
                        verify=False
                    )
                
                st.success(f"Status Code: {response.status_code}")
                st.json(response.json() if "application/json" in response.headers.get("Content-Type", "") else {"text": response.text})
            except Exception as e:
                st.error(f"Erro: {e}")

# ==========================================
# ABA 2: PASSIVA - ENVIAR SOAP XML
# ==========================================
with tab_soap:
    st.header("Integração Passiva: Consumo SOAP (Estrutura XML)")
    
    default_wsdl = "http://services.toledobrasil.com/WS_GUARDIAN/WS_GUARDIAN_PLUS.asmx?wsdl"
    wsdl_input = st.text_input("URL do WSDL", value=default_wsdl)
    
    wsdl_url = wsdl_input.strip()
    if wsdl_url and not wsdl_url.startswith(("http://", "https://")):
        wsdl_url = "http://" + wsdl_url
        
    inferred_endpoint = wsdl_url.split("?")[0] if "?" in wsdl_url else wsdl_url

    if st.button("Carregar WSDL e Mapear Métodos", use_container_width=True):
        try:
            with st.spinner("Lendo documento WSDL da Toledo Brasil..."):
                settings = Settings(strict=False, xml_huge_tree=True)
                client = Client(wsdl=wsdl_url, settings=settings)
                st.session_state.soap_client = client
                st.success("✅ Estruturas WSDL mapeadas com sucesso!")
        except Exception as e:
            st.error(f"Erro ao carregar o WSDL: {e}")

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
            selected_operation = st.selectbox("Operação (WebMethod)", operations)
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
            
        st.markdown("**Envelope SOAP XML (Edite os valores dos campos diretamente no XML)**")
        soap_xml_payload = st.text_area("Corpo da Mensagem SOAP", value=xml_template, height=350)
        
        if st.button("Disparar Requisição SOAP XML", type="primary", use_container_width=True):
            try:
                with st.spinner(f"Disparando XML bruto para o método {selected_operation}..."):
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
                    st.success(f"✅ Executado com Sucesso! Status Code: {response.status_code}")
                else:
                    st.error(f"⚠️ Resposta do Servidor com Erro. Status Code: {response.status_code}")
                
                st.markdown("**XML de Resposta Recebido:**")
                st.code(response.text, language="xml")
                
            except Exception as e:
                st.error(f"Erro Crítico de Conexão: {e}")

# ==========================================
# ABA 3: ATIVA - MONITORAMENTO REMOTO
# ==========================================
with tab_monitor:
    st.header("Integração Ativa: Webhooks Recebidos na VM")
    st.markdown("Esta aba monitoriza as requisições buscando os dados dinamicamente da API na sua VM.")
    
    if st.button("Atualizar Lista 🔄"):
        pass 
            
    try:
        url_logs = f"{api_base_url}/api/logs"
        with st.spinner("Buscando logs do servidor remoto..."):
            response = requests.get(url_logs, timeout=5)
            
        if response.status_code == 200:
            logs = response.json()
            
            if not logs:
                st.info("Nenhuma requisição intercetada até ao momento na VM.")
            else:
                for idx, log in enumerate(logs):
                    with st.expander(f"[{log['data_hora']}] Requisição {log['tipo']} Detetada"):
                        st.markdown(f"**Headers Originais:**")
                        st.json(log["headers"])
                        st.markdown(f"**Conteúdo Recebido (Payload):**")
                        if log["tipo"] == "REST":
                            st.json(log["payload"])
                        else:
                            st.code(log["payload"], language="xml")
        else:
            st.error(f"Erro ao falar com a API da VM. Status Code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Não foi possível conectar ao servidor em `{api_base_url}`.\n\n"
                 f"**Passos para resolução:**\n"
                 f"1. Garanta que o comando `uvicorn ativa:app --host 0.0.0.0 --port 8000` está em execução no terminal SSH da sua VM.\n"
                 f"2. Certifique-se de que criou a regra de **Firewall no GCP** para abrir a porta **8000** (protocolo TCP) para o tráfego de origem `0.0.0.0/0`.")
    except Exception as e:
        st.error(f"Erro de Execução: {e}")