import streamlit as st
import os

from pipeline import process_uploaded_file


st.set_page_config(
    page_title="Pipeline de Mídia com IA"
)


# ---------------------------------
# FUNÇÃO PARA LIMPAR ESTADO
# QUANDO O ARQUIVO FOR REMOVIDO
# ---------------------------------

def clear_result():

    if "result" in st.session_state:
        del st.session_state["result"]



# ---------------------------------
# INTERFACE
# ---------------------------------

st.title("🎬 A/V Text Transformer")


uploaded_file = st.file_uploader(
    "Escolha um arquivo",
    type=[
        "mp4",
        "mov",
        "avi",
        "mkv",
        "mp3",
        "wav",
        "m4a",
        "aac",
        "flac",
        "ogg"
    ],
    key="uploaded_file",
    on_change=clear_result
)



# ---------------------------------
# PROCESSAMENTO
# ---------------------------------

if uploaded_file:

    st.success(
        f"Arquivo: {uploaded_file.name}"
    )


    if st.button("🚀 Processar"):

        with st.spinner(
            "Processando..."
        ):


            result = process_uploaded_file(
                uploaded_file
            )


            # Guarda resultado na sessão
            st.session_state["result"] = result


            st.success(
                "✅ Concluído!"
            )



# ---------------------------------
# DOWNLOAD + INFORMAÇÕES
# PERMANECEM APÓS DOWNLOAD
# ---------------------------------

if "result" in st.session_state:


    result = st.session_state["result"]


    st.subheader(
        "📥 Download dos arquivos"
    )


    for path in result["paths"]:


        with open(
            path,
            "rb"
        ) as file:


            st.download_button(

                label=f"⬇️ Baixar {os.path.basename(path)}",

                data=file,

                file_name=os.path.basename(path),

                mime="text/plain"

            )



    # ---------------------------------
    # CUSTOS
    # ---------------------------------

    st.subheader(
        "💰 Estimativa vs Real"
    )


    st.write(
        f"Duração: {result['duration']:.2f} segundos"
    )


    st.write(
        f"Estimativa transcrição: ${result['estimated_cost']:.4f}"
    )


    usage = result["usage"]


    total_cost = sum(
        v["cost"]
        for v in usage.values()
    )


    st.write(
        f"Custo real total: ${total_cost:.4f}"
    )