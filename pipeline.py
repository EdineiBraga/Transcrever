import os
import tempfile
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, AudioFileClip
from openai import OpenAI
from pathlib import Path

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUPPORTED_AUDIO = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"]
SUPPORTED_VIDEO = [".mp4", ".mov", ".avi", ".mkv"]

CHUNK_DURATION = 300
NO_CHUNK_THRESHOLD = 600  # 10 minutos

TOKEN_LOG = {
    "transcricao": {"tokens": 0, "cost": 0},
    "processamento": {"tokens": 0, "cost": 0},
}

PRICING = {
    "gpt-4o-mini_input": 0.00015,
    "gpt-4o-mini_output": 0.0006,
}


# -------------------------------
# UTIL
# -------------------------------
def estimate_tokens(text):
    return max(1, int(len(text) / 4))


def estimate_transcription_cost(duration_sec):
    return (duration_sec / 60) * 0.006


def add_usage(stage, input_tokens=0, output_tokens=0, duration_sec=0):

    if stage == "transcricao":

        cost = estimate_transcription_cost(duration_sec)

        TOKEN_LOG[stage]["tokens"] += estimate_tokens(str(duration_sec))
        TOKEN_LOG[stage]["cost"] += cost

    else:

        cost = (
            (input_tokens / 1000) * PRICING["gpt-4o-mini_input"]
            +
            (output_tokens / 1000) * PRICING["gpt-4o-mini_output"]
        )

        TOKEN_LOG[stage]["tokens"] += input_tokens + output_tokens
        TOKEN_LOG[stage]["cost"] += cost



# -------------------------------
# SAVE FILE
# -------------------------------
def save_uploaded_file(uploaded_file):

    suffix = os.path.splitext(uploaded_file.name)[1]

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    chunk_size = 1024 * 1024

    uploaded_file.seek(0)

    while True:

        data = uploaded_file.read(chunk_size)

        if not data:
            break

        temp.write(data)

    temp.close()

    return temp.name



# -------------------------------
# EXTRAÇÃO
# -------------------------------
def extract_audio_if_needed(file_path):

    ext = os.path.splitext(file_path)[1].lower()


    if ext in SUPPORTED_AUDIO:
        return file_path, None


    if ext in SUPPORTED_VIDEO:

        clip = VideoFileClip(file_path)

        temp_audio = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False
        )

        audio_path = temp_audio.name


        clip.audio.write_audiofile(audio_path)

        duration = clip.duration

        clip.close()


        return audio_path, duration


    raise ValueError(f"Formato não suportado: {ext}")



# -------------------------------
# SPLIT
# -------------------------------
def split_audio(audio_path):

    clip = AudioFileClip(audio_path)

    duration = clip.duration

    chunks = []

    start = 0


    while start < duration:

        end = min(start + CHUNK_DURATION, duration)


        temp_chunk = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False
        )

        chunk_path = temp_chunk.name


        subclip = clip.subclip(start, end)

        subclip.write_audiofile(chunk_path)


        chunks.append(
            (chunk_path, end - start)
        )


        start += CHUNK_DURATION


    clip.close()

    return chunks, duration



# -------------------------------
# TRANSCRIÇÃO
# -------------------------------
def transcribe(audio_path):

    clip = AudioFileClip(audio_path)

    duration = clip.duration

    clip.close()


    if duration < NO_CHUNK_THRESHOLD:


        with open(audio_path, "rb") as f:

            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )


        add_usage(
            "transcricao",
            duration_sec=duration
        )


        return result.text, duration



    chunks, total_duration = split_audio(audio_path)

    texts = []


    for chunk_path, dur in chunks:


        with open(chunk_path, "rb") as f:

            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )


        texts.append(result.text)

        os.remove(chunk_path)


    add_usage(
        "transcricao",
        duration_sec=total_duration
    )


    return "\n".join(texts), total_duration



# -------------------------------
# IA
# -------------------------------
def process_text(text):

    text = text[:8000]

    input_tokens = estimate_tokens(text)


    response = client.chat.completions.create(

        model="gpt-4o-mini",

        messages=[

            {
                "role": "system",
                "content":
                (
                    "Você é um especialista técnico.\n\n"
                    "TAREFAS OBRIGATÓRIAS:\n"
                    "1) Traduza TODO o texto para português do Brasil.\n"
                    "2) Gere um resumo técnico claro em português.\n\n"
                    "FORMATO:\n"
                    "TRADUÇÃO:\n"
                    "<texto traduzido>\n\n"
                    "RESUMO:\n"
                    "<resumo técnico>"
                )
            },

            {
                "role": "user",
                "content": text
            }

        ]
    )


    output = response.choices[0].message.content


    add_usage(
        "processamento",
        input_tokens,
        estimate_tokens(output)
    )


    return output



# -------------------------------
# PIPELINE
# -------------------------------
def process_uploaded_file(uploaded_file):

    temp_path = save_uploaded_file(uploaded_file)


    audio_path, _ = extract_audio_if_needed(
        temp_path
    )


    text, duration = transcribe(
        audio_path
    )


    result_text = process_text(text)



    # ALTERAÇÃO:
    # cria pasta temporária no servidor
    # para depois disponibilizar download

    output_dir = tempfile.mkdtemp()


    filename = os.path.splitext(
        uploaded_file.name
    )[0]


    base = os.path.join(
        output_dir,
        filename
    )


    result_path = base + "_resultado.txt"

    tokens_path = base + "_tokens.txt"



    with open(
        result_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(result_text)



    with open(
        tokens_path,
        "w",
        encoding="utf-8"
    ) as f:

        for k, v in TOKEN_LOG.items():

            f.write(
                f"{k}: tokens={v['tokens']} cost=${v['cost']:.6f}\n"
            )



    return {

        "usage": TOKEN_LOG,

        "duration": duration,

        "estimated_cost":
            estimate_transcription_cost(duration),

        "paths":
            [
                result_path,
                tokens_path
            ]
    }