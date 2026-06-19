import streamlit as st
import os

from pipeline import process_uploaded_file


st.set_page_config(
    page_title="Pipeline de Mídia com IA"
)


st.title(
    "🎬 A/V Text Transformer"
)


uploaded_file = st.file_uploader(

    "Escolha um arquivo",

    type=[
        "mp4","mov","avi","mkv",
        "mp3","wav","m4a",
        "aac","flac","ogg"
    ]
)



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


            st.success(
                "✅ Concluído!"
            )


            st.subheader(
                "📥 Baixar arquivos"
            )


            for path in result["paths"]:


                with open(
                    path,
                    "rb"
                ) as file:


                    st.download_button(

                        label=
                        f"⬇️ {os.path.basename(path)}",

                        data=file,

                        file_name=
                        os.path.basename(path),

                        mime="text/plain"
                    )



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