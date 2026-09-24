from flask import Flask, render_template_string, request, session, url_for
import random
import os
import sympy
from sympy import sympify
import sqlite3
import uuid
import requests
from bs4 import BeautifulSoup
try:
    from duckduckgo_search import DDGS
except ModuleNotFoundError:
    DDGS = None
from datetime import datetime
import re
from langdetect import detect

CHISTES = [
    "“Me encantan los mensajes de voz”. “Yo los detesto”. “Sí, esos también molan”.",
    "¿Qué hace un mudo bailando? Una mudanza.",
    "“Hola, busco trabajo”. “¿Le interesa de jardinero?”. “¿Dejar dinero? ¡Si lo que busco es trabajo!”.",
    "¿Qué le dice una impresora a otra? Esta hoja es tuya o es impresión mía?",
    "“Me acabo de tirar un pedo de esos silenciosos, ¿qué hago?”. “Ahora nada, pero cuando llegues a casa, cámbiale las pilas al audífono”.",
    "“Me han despedido”. “¿Y qué vas a hacer?”. “Croquetas”. “Digo con tu vida”. “Pues comerme unas croquetas”.",
    "¿Por qué el libro de matemáticas estaba triste?Porque tenía muchos problemas.",
    "¿Qué le dice un imán a otro imán?¡Me atraes!",
    "¿Por qué los pájaros no usan Facebook? Porque ya tienen Twitter.",
    "¿Qué le dice una pared a otra pared?¡Nos vemos en la esquina!",
    "¿Por qué los pájaros vuelan hacia el sur en invierno? — ¡Porque caminando tardarían demasiado!",
    "¿Qué hace una abeja en el gimnasio? — ¡Zum-ba!",
    "¿Qué le dice un techo a otro techo? — Nada, los techos no hablan.",
    "¿Qué le dijo el semáforo al coche? — No me mires, que me estoy cambiando.",
    "¿Por qué los esqueletos no pueden mentir? — Porque todo el mundo les ve el interior.",
    "¿Qué le dice un GPS a otro? — Me tienes loco, siempre dando vueltas.",
    "¿Por qué los matemáticos son buenos en las fiestas? — Porque saben cómo dividir la cuenta.",
    "Cuál es el colmo de un astrónomo? — Que su novia sea una estrella… pero de cine.",
    "¿Cuál es el colmo de un electricista? — Que su hijo se llame Ernesto... ¡y no le haga ni chispa!",
    "¿Cuál es el colmo de un pintor? — Que su vida sea de color gris y su mujer le dé una brocha.",
    "¿Cuál es el colmo de un profesor? — Que sus alumnos le suspendan la vida y su mujer le ponga deberes.",
    "¿Cuál es el colmo de un matemático? — Que su mujer le sume problemas, le reste el sueldo, le divida la familia y encima no le cuente nada.",
    "¿Cuál es el colmo de un mago? — Que su mujer desaparezca... ¡pero con el dinero!",
    "Papá, ¿qué se siente tener un hijo tan guapo e inteligente? No sé, pregúntale a tu abuelo.",
    "¿Cómo se queda un mago después de comer? Magordito.",
]

FRASES_NO_RESULTADO = {
    'es': [
        "Intenta preguntar de otra forma.",
        "Se ha producido un ERROR.",
        "Lo siento, no he entendido lo que te refieres"
    ],
    'en': [
        "I couldn't find a clear answer on the web. Try asking in another way.",
        "I did not find the answer, but you can try a different question.",
        "Sorry, I couldn't find a precise answer right now."
    ]
}

def descargar_web(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        respuesta = requests.get(url, headers=headers, timeout=5)
        if respuesta.status_code != 200:
            return None
        return respuesta.text
    except:
        return None

def limpiar_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    texto = soup.get_text(separator=" ", strip=True)
    texto = re.sub(r'\s+', ' ', texto)
    if len(texto) < 100:
        return None
    return texto[:1000]


def detectar_idioma(texto):
    if not texto:
        return 'es'

    texto_norm = re.sub(r'[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s]', ' ', texto.lower())
    texto_norm = re.sub(r'\s+', ' ', texto_norm).strip()

    if not texto_norm:
        return 'es'

    spanish_markers = [
        'hola', 'buenas', 'buenos', 'adios', 'adiós', 'gracias', 'por favor', 'ayuda',
        'como', 'qué', 'cuanto', 'cuánto', 'quien', 'quién', 'donde', 'dónde', 'mi nombre',
        'chiste', 'resultado', 'sabes', 'llamas', 'llamo', 'hoy', 'te llamas', 'que tal',
        'cuéntame', 'cuentame', 'yo soy'
    ]
    english_markers = [
        'hello', 'hi', 'hey', 'goodbye', 'bye', 'thanks', 'please', 'help', 'how are you',
        'what', 'where', 'who', 'my name is', 'who are you', 'what is your name', 'what time',
        'tell me a joke', 'joke', 'do you like python', 'python', 'how', 'where are you'
    ]

    if any(marker in texto_norm for marker in spanish_markers):
        return 'es'
    if any(marker in texto_norm for marker in english_markers):
        return 'en'

    try:
        idioma = detect(texto_norm or 'es')
        if idioma.startswith('es'):
            return 'es'
        if idioma.startswith('en'):
            return 'en'
        if idioma.startswith('fr'):
            return 'fr'
        if idioma.startswith('de'):
            return 'de'
        if idioma.startswith('pt'):
            return 'pt'
        return idioma
    except Exception:
        return 'es'


def texto_en_idioma(idioma, textos):
    return textos.get(idioma) or textos.get('es') or next(iter(textos.values()))


def respuesta_conocimiento_basico(query, idioma):
    q = (query or '').lower().strip()
    if 'cristiano ronaldo' in q or 'cristiano' in q and 'ronaldo' in q:
        return texto_en_idioma(idioma, {
            'es': 'Cristiano Ronaldo es un futbolista portugués, ampliamente considerado uno de los mejores de la historia. Ha ganado numerosos títulos, trofeos individuales y fue capitán de la selección de Portugal.',
            'en': 'Cristiano Ronaldo is a Portuguese footballer, widely considered one of the greatest players in football history. He has won many titles, individual awards, and captained the Portugal national team.'
        })
    if 'messi' in q:
        return texto_en_idioma(idioma, {
            'es': 'Lionel Messi es un futbolista argentino, considerado uno de los mejores del mundo. Jugó muchos años en el FC Barcelona y ganó múltiples trofeos internacionales.',
            'en': 'Lionel Messi is an Argentine footballer, widely regarded as one of the greatest players ever. He spent many years at FC Barcelona and won multiple international trophies.'
        })
    if 'java' in q:
        return texto_en_idioma(idioma, {
            'es': 'Java es un lenguaje de programación orientado a objetos muy usado en empresas, aplicaciones empresariales y Android.',
            'en': 'Java is a popular object-oriented programming language used in enterprise software, backend development, and Android apps.'
        })
    if 'python' in q:
        return texto_en_idioma(idioma, {
            'es': 'Python es un lenguaje de programación muy popular por su simplicidad, legibilidad y uso en IA, automatización y desarrollo web.',
            'en': 'Python is a very popular programming language thanks to its simplicity, readability, and use in AI, automation, and web development.'
        })
    return None


def resumir_texto(texto, max_chars=280):
    texto = re.sub(r'\s+', ' ', texto or '').strip()
    if not texto:
        return ''

    texto = re.sub(r'\b(ver m\u00e1s|leer m\u00e1s|descargar|enlace|hace \d+ d\u00edas)\b', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\s+', ' ', texto).strip()

    frases = [f.strip() for f in re.split(r'(?<=[.!?])\s+', texto) if f.strip()]
    if len(frases) >= 2:
        resumen = ' '.join(frases[:2])
    elif frases:
        resumen = frases[0]
    else:
        resumen = texto

    resumen = re.sub(r'^(Titulo|Title|Resumen)\s*[:\-]\s*', '', resumen, flags=re.IGNORECASE)

    if len(resumen) > max_chars:
        resumen = resumen[:max_chars].rsplit(' ', 1)[0].rstrip()
    return resumen


def guardar_historial(usuario, rol, contenido):
    conn = sqlite3.connect('memoria_ia.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO historial (usuario, fecha, rol, contenido) VALUES (?, ?, ?, ?)",
        (usuario, datetime.utcnow().isoformat(), rol, contenido)
    )
    conn.commit()
    conn.close()


def cargar_historial(usuario, limite=50):
    conn = sqlite3.connect('memoria_ia.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rol, contenido FROM historial WHERE usuario=? ORDER BY fecha DESC LIMIT ?",
        (usuario, limite)
    )
    filas = cursor.fetchall()
    conn.close()
    return [{"role": rol, "content": contenido} for rol, contenido in reversed(filas)]


def buscar_duckduckgo(query, idioma):
    if DDGS is None:
        return []

    try:
        codigo_region = 'es-es'
        mapa_regiones = {
            'es': 'es-es',
            'de': 'de-de',
            'zh': 'zh-cn',
            'en': 'us-en',
            'fr': 'fr-fr',
            'pt': 'pt-br'
        }
        if idioma in mapa_regiones:
            codigo_region = mapa_regiones[idioma]

        with DDGS() as ddgs:
            resultados = list(ddgs.text(
                keywords=query,
                region=codigo_region,
                safesearch='moderate',
                max_results=6
            ))
        return resultados
    except Exception:
        return []


def obtener_respuesta_web(query, idioma):
    resultados = buscar_duckduckgo(query, idioma)
    if not resultados:
        return None

    fuentes = []
    fallback = None

    for res in resultados:
        titulo = (res.get('title') or '').strip()
        cuerpo = (res.get('body') or '').strip()
        enlace = (res.get('href') or res.get('url') or res.get('link') or '').strip()

        if not titulo and not cuerpo:
            continue

        if enlace and len(cuerpo) < 120:
            html = descargar_web(enlace)
            if html:
                texto_limpio = limpiar_html(html)
                if texto_limpio:
                    cuerpo = texto_limpio

        if not cuerpo:
            continue

        if any(x in cuerpo.lower() for x in ["search settings", "loc. pronom", "yuasa", "skincare"]):
            continue

        texto_total = (titulo + ' ' + cuerpo).strip()
        try:
            idioma_detectado = detectar_idioma(texto_total)
            if idioma_detectado == idioma:
                pass
            elif idioma_detectado not in ['es', 'en'] and idioma in ['es', 'en']:
                pass
        except Exception:
            pass

        texto_fuente = (titulo + '. ' + cuerpo).strip() or cuerpo or titulo
        texto_fuente = re.sub(r"(enlaces|descripción|hace \d+ días|ver más|search settings|loc\. pronom\.)", "", texto_fuente, flags=re.IGNORECASE)
        respuesta = resumir_texto(texto_fuente, max_chars=220)
        respuesta = re.sub(r'[\.]{2,}$', '', respuesta).strip()

        if not respuesta:
            continue

        if enlace:
            fuentes.append({
                'titulo': titulo or 'Fuente web',
                'url': enlace,
                'snippet': cuerpo[:180]
            })

        if fallback is None:
            fallback = {
                'respuesta': respuesta,
                'fuentes': list(fuentes),
            }

        # Si el resultado coincide con el idioma del usuario, lo devolvemos directamente.
        try:
            idioma_detectado = detectar_idioma(texto_fuente)
            if idioma_detectado == idioma or (idioma == 'es' and idioma_detectado in ['es', 'en']) or (idioma == 'en' and idioma_detectado in ['en', 'es']):
                return {
                    'respuesta': respuesta,
                    'fuentes': fuentes,
                }
        except Exception:
            pass

    return fallback

def init_db():
    conn = sqlite3.connect('memoria_ia.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS recuerdos 
                      (usuario TEXT, clave TEXT, valor TEXT, PRIMARY KEY (usuario, clave))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial
                      (usuario TEXT, fecha TEXT, rol TEXT, contenido TEXT)''')
    conn.commit()
    conn.close()

init_db()

def guardar_recuerdo(usuario, clave, valor):
    conn = sqlite3.connect('memoria_ia.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO recuerdos (usuario, clave, valor) VALUES (?, ?, ?)", 
                   (usuario, clave, valor))
    conn.commit()
    conn.close()

def obtener_recuerdo(usuario, clave):
    conn = sqlite3.connect('memoria_ia.db')
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM recuerdos WHERE usuario=? AND clave=?", (usuario, clave))
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else None

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_change_in_production')

HTML_CHILD = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ConversAItion</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --bg: #02060b;
            --bg-soft: #0a1017;
            --panel: rgba(13, 18, 24, 0.9);
            --panel-strong: #0e141c;
            --line: rgba(255,255,255,0.12);
            --text: #f5f7fb;
            --muted: #dfeaf9;
            --user: #f0f3ff;
            --user-text: #131922;
            --bot: rgba(255,255,255,0.03);
            --accent: #8ec5ff;
            --accent-2: #7cf0ff;
            --accent-3: #ff5bd1;
            --shadow: 0 18px 40px rgba(0,0,0,0.45);
        }

        * { box-sizing: border-box; }
        html, body {
            margin: 0;
            min-height: 100%;
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
        }

        body {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            background:
                radial-gradient(circle at top center, rgba(120, 180, 255, 0.08), transparent 22%),
                radial-gradient(circle at 80% 15%, rgba(255, 92, 209, 0.05), transparent 18%),
                #02060b;
        }

        .app-shell {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            position: relative;
        }

        .topbar {
            position: relative;
            padding: 26px 28px 18px;
            border-bottom: 1px solid var(--line);
            background: rgba(2, 8, 12, 0.78);
            backdrop-filter: blur(10px);
        }

        .brand-wrap {
            position: relative;
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 92px;
        }

        .brand-mini {
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 10px;
            border-radius: 12px;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02);
        }

        .mini {
            width: 12px;
            height: 12px;
            border-radius: 3px;
            display: block;
            box-shadow: 0 0 12px rgba(255,255,255,0.2);
        }

        .mini-1 { background: linear-gradient(135deg, #56d8ff, #2f80ed); }
        .mini-2 { background: linear-gradient(135deg, #c3ff5d, #6ee7b7); }
        .mini-3 { background: linear-gradient(135deg, #ff7cc8, #ffb86d); }
        .mini-4 { background: linear-gradient(135deg, #9a7cff, #4ad0ff); }
        .mini-5 { background: linear-gradient(135deg, #f44336, #ffb347); }

        .brand-title {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: clamp(3rem, 5vw, 5.2rem);
            line-height: 1;
            font-weight: 900;
            letter-spacing: -0.08em;
            background: linear-gradient(90deg, #56e1ff 0%, #3b82f6 18%, #8b5cf6 35%, #f472b6 52%, #fbbf24 72%, #7ef9a9 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 0 24px rgba(94, 150, 255, 0.18);
            user-select: none;
        }

        .brand-ai {
            background: linear-gradient(180deg, #dbeafe 0%, #67e8f9 25%, #7c3aed 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 0 18px rgba(124, 58, 237, 0.35);
        }

        .beta-tag {
            position: absolute;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            display: flex;
            align-items: center;
            justify-content: center;
            width: 118px;
            height: 118px;
        }

        .beta-pill {
            position: relative;
            z-index: 1;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 112px;
            height: 112px;
            border-radius: 50%;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.12);
            font-size: 0.85rem;
            font-weight: 800;
            color: #edf5ff;
            letter-spacing: 0.08rem;
            text-shadow: 0 0 18px rgba(255,255,255,0.4);
            box-shadow: inset 0 0 25px rgba(255,255,255,0.02), 0 0 25px rgba(96,165,250,0.14);
            animation: betaPulse 5s ease-in-out infinite;
        }

        .beta-orbit {
            position: absolute;
            inset: 0;
            border-radius: 50%;
            border: 1px solid rgba(255,255,255,0.12);
            animation: orbit 6s linear infinite;
            box-shadow: inset 0 0 18px rgba(255,255,255,0.02);
        }

        .beta-orbit::before {
            content: "";
            position: absolute;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: linear-gradient(135deg, #8fe8ff, #5ba1ff);
            top: 12px;
            left: 50%;
            transform: translateX(-50%);
            box-shadow: 0 0 18px rgba(96,165,250,0.9);
        }

        @keyframes betaPulse {
            0%, 100% { opacity: 0.8; transform: scale(0.96); }
            50% { opacity: 1; transform: scale(1); }
        }

        @keyframes orbit {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .chat-panel {
            width: min(100%, 920px);
            margin: 0 auto;
            padding: 18px 18px 10px;
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .msg {
            max-width: min(84%, 700px);
            padding: 14px 18px;
            border-radius: 22px;
            line-height: 1.5;
            font-size: 1rem;
            word-break: break-word;
            box-shadow: var(--shadow);
        }

        .msg.bot {
            align-self: flex-start;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--line);
            color: var(--muted);
        }

        .msg.user {
            align-self: flex-end;
            background: linear-gradient(135deg, #ffffff, #edf4ff);
            color: var(--user-text);
            font-weight: 600;
        }

        .composer-wrap {
            width: min(100%, 900px);
            margin: 0 auto;
            padding: 18px 18px 32px;
        }

        .composer {
            display: flex;
            align-items: center;
            gap: 12px;
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 999px;
            background: rgba(16, 21, 28, 0.94);
            padding: 10px 10px 10px 18px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.26), inset 0 0 0 1px rgba(255,255,255,0.02);
        }

        .composer input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text);
            font-size: 1.05rem;
            padding: 10px 8px;
        }

        .composer input::placeholder {
            color: rgba(255,255,255,0.52);
        }

        .send-btn {
            width: 60px;
            height: 60px;
            border: none;
            border-radius: 50%;
            background: linear-gradient(135deg, #f4f8ff, #e7ecff 18%, #d7e7ff 100%);
            color: #111827;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0;
            transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
            box-shadow: 0 12px 24px rgba(255,255,255,0.12);
            cursor: pointer;
        }

        .send-btn:hover {
            transform: translateY(-2px) scale(1.02);
            filter: brightness(1.04);
            box-shadow: 0 15px 28px rgba(255,255,255,0.18);
        }

        .send-btn img {
            width: 23px;
            height: 23px;
            display: block;
        }

        .floating-tools {
            position: fixed;
            right: 24px;
            bottom: 155px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            z-index: 10;
        }

        .tool-btn {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            border: 1px solid rgba(255,255,255,0.15);
            background: rgba(255,255,255,0.02);
            color: #eaf2ff;
            font-size: 1.25rem;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 12px 20px rgba(0,0,0,0.28);
            backdrop-filter: blur(8px);
        }

        .intro-overlay {
            position: fixed;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #000;
            z-index: 2000;
            cursor: pointer;
        }

        .intro-overlay.hidden {
            display: none;
        }

        .intro-video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            background: #000;
        }

        @media (max-width: 900px) {
            .topbar {
                padding: 24px 18px 14px;
            }
            .brand-wrap {
                min-height: 80px;
            }
            .brand-mini {
                gap: 5px;
                padding: 6px 8px;
            }
            .mini {
                width: 10px;
                height: 10px;
            }
            .brand-title {
                font-size: clamp(3.2rem, 6.5vw, 4.8rem);
            }
            .beta-tag {
                width: 90px;
                height: 90px;
            }
            .beta-pill {
                width: 82px;
                height: 82px;
                font-size: 0.68rem;
            }
            .chat-panel {
                padding: 12px 14px 6px;
            }
            .composer-wrap {
                padding: 12px 14px 22px;
            }
            .floating-tools {
                right: 16px;
                bottom: 140px;
            }
        }

        @media (max-width: 576px) {
            .topbar {
                padding: 18px 12px 12px;
            }
            .brand-wrap {
                min-height: 68px;
            }
            .brand-mini {
                display: none;
            }
            .beta-tag {
                width: 72px;
                height: 72px;
            }
            .beta-pill {
                width: 68px;
                height: 68px;
                font-size: 0.54rem;
                letter-spacing: 0.06rem;
            }
            .brand-title {
                font-size: clamp(2.8rem, 9vw, 4rem);
            }
            .msg {
                max-width: 90%;
                padding: 12px 14px;
                border-radius: 18px;
                font-size: 0.95rem;
            }
            .composer {
                gap: 8px;
                padding: 8px 8px 8px 14px;
            }
            .composer input {
                font-size: 1rem;
                padding: 8px 4px;
            }
            .send-btn {
                width: 48px;
                height: 48px;
            }
            .floating-tools {
                right: 12px;
                bottom: 128px;
                gap: 10px;
            }
            .tool-btn {
                width: 42px;
                height: 42px;
                font-size: 1.1rem;
            }
        }
    </style>
</head>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-Z27SZT3V4E"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-Z27SZT3V4E');
</script>
<body>
    {% if primera_vez %}
    <div id="intro-overlay" class="intro-overlay">
        <video id="intro-video" class="intro-video" src="{{ url_for('static', filename='Intro.mp4') }}" autoplay muted playsinline preload="auto"></video>
    </div>
    {% endif %}

    <div class="app-shell">
        <header class="topbar">
            <div class="brand-wrap">
                <div class="brand-mini" aria-hidden="true">
                    <span class="mini mini-1"></span>
                    <span class="mini mini-2"></span>
                    <span class="mini mini-3"></span>
                    <span class="mini mini-4"></span>
                    <span class="mini mini-5"></span>
                </div>
                <div class="brand-title">Convers<span class="brand-ai">AI</span>tion</div>
                <div class="beta-tag">
                    <div class="beta-orbit"></div>
                    <div class="beta-pill">0.3 BETA</div>
                </div>
            </div>
        </header>

        <main class="chat-panel" id="chat">
            {% for msg in history %}
                <div class="msg {{ msg.role }}">{{ msg.content }}</div>
            {% endfor %}
        </main>

        <div class="floating-tools" aria-hidden="true">
            <button class="tool-btn" type="button">✦</button>
            <button class="tool-btn" type="button">◌</button>
            <button class="tool-btn" type="button">◉</button>
        </div>

        <div class="composer-wrap">
            <form class="composer" method="POST">
                <input type="text" name="message" placeholder="Escribe tu consulta..." required autocomplete="off">
                <button class="send-btn" type="submit" aria-label="Enviar">
                    <img src="{{ url_for('static', filename='Up-Arrow.png') }}" alt="Enviar">
                </button>
            </form>
        </div>
    </div>

    <script>
        const chat = document.getElementById('chat');
        if (chat) chat.scrollTop = chat.scrollHeight;

        const introOverlay = document.getElementById('intro-overlay');
        const introVideo = document.getElementById('intro-video');

        function finishIntro() {
            if (!introOverlay || !introVideo) return;
            introVideo.pause();
            introVideo.currentTime = introVideo.duration || 0;
            introOverlay.classList.add('hidden');
        }

        if (introOverlay && introVideo) {
            introVideo.volume = 1;
            introVideo.muted = true;

            introVideo.addEventListener('playing', () => {
                introVideo.muted = false;
                introVideo.volume = 1;
            });

            introVideo.addEventListener('ended', finishIntro);
            introOverlay.addEventListener('click', finishIntro);
            window.addEventListener('load', () => {
                introVideo.play().catch(() => {});
            });
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    primera_vez = 'seen_intro' not in session
    if primera_vez:
        session['seen_intro'] = True

    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

    user_id = session['user_id']
    if 'history' not in session:
        session['history'] = cargar_historial(user_id)

    user_input = request.form.get('message')
    respuesta = ""
    fuentes = []

    history = list(session.get('history', []))

    if user_input:
        idioma_actual = detectar_idioma(user_input)
        session['idioma'] = idioma_actual

        history.append({"role": "user", "content": user_input})
        guardar_historial(user_id, 'user', user_input)
        mensaje_clean = user_input.lower().strip()

        if "mi " in mensaje_clean and " es " in mensaje_clean and " me " in mensaje_clean:
            partes = mensaje_clean.replace("mi ", "").split(" es ")
            clave = partes[0].strip()
            valor = partes[1].strip()
            guardar_recuerdo(user_id, clave, valor)
            respuesta = texto_en_idioma(idioma_actual, {
                'es': f"¡Entendido! Recordaré que tu {clave} es {valor}.",
                'en': f"Got it! I'll remember that your {clave} is {valor}."
            })

        elif "my name is" in mensaje_clean:
            nombre = mensaje_clean.split("my name is")[-1].strip()
            guardar_recuerdo(user_id, "nombre", nombre)
            respuesta = texto_en_idioma(idioma_actual, {
                'es': f"¡Encantado, {nombre}! ¿De qué hablamos hoy?",
                'en': f"Nice to meet you, {nombre}! What would you like to talk about today?"
            })

        elif any(x in mensaje_clean for x in ["como me llamo", "quien soy", "what is my name", "who am i"]):
            nombre = obtener_recuerdo(user_id, "nombre")
            respuesta = texto_en_idioma(idioma_actual, {
                'es': f"Te llamas {nombre}." if nombre else "Aún no me has dicho tu nombre.",
                'en': f"Your name is {nombre}." if nombre else "You haven't told me your name yet."
            })

        elif any(x in mensaje_clean for x in ["que sabes de mi", "what do you know about me"]):
            conn = sqlite3.connect('memoria_ia.db')
            cursor = conn.cursor()
            cursor.execute("SELECT clave, valor FROM recuerdos WHERE usuario=?", (user_id,))
            todos = cursor.fetchall()
            conn.close()
            if todos:
                datos = [f"{c}: {v}" for c, v in todos]
                respuesta = texto_en_idioma(idioma_actual, {
                    'es': "Esto es lo que recuerdo: " + ", ".join(datos) + ".",
                    'en': "This is what I remember: " + ", ".join(datos) + "."
                })
            else:
                respuesta = texto_en_idioma(idioma_actual, {
                    'es': "Aún no sé nada personal de ti.",
                    'en': "I don't know anything personal about you yet."
                })

        elif any(x in mensaje_clean for x in ["hola", "buenas", "moin", "hello", "hi", "hey"]):
            respuesta = texto_en_idioma(idioma_actual, {
                'es': "¡Hola! ¿Qué tal estás?",
                'en': "Hello! How are you?"
            })

        elif any(x in mensaje_clean for x in ["quien eres", "who are you"]):
            respuesta = texto_en_idioma(idioma_actual, {
                'es': "Soy ConversAItion y pertenezco a la empresa CrAIthon. Todavía soy una IA bastante sencilla, pero en el futuro voy a mejorar. Por ahora, busco información en internet.",
                'en': "I'm ConversAItion from CrAIthon. I'm a simple AI for now, but I can search the web and learn from this conversation."
            })

        elif any(x in mensaje_clean for x in ["te gusta python", "do you like python"]):
            respuesta = texto_en_idioma(idioma_actual, {
                'es': "¡Me encanta! Es mi lenguaje nativo y además es la primera lengua que aprendieron mis creadores.",
                'en': "I love it! Python is my native programming language and the first one my creators taught me."
            })

        elif any(x in mensaje_clean for x in ["adiós", "adios", "goodbye", "bye"]):
            respuesta = texto_en_idioma(idioma_actual, {
                'es': "¡Adiós! Cuando quieras seguimos!!!",
                'en': "Goodbye! I'm here when you want to continue."
            })

        elif any(x in mensaje_clean for x in ["que tal estás", "qué tal estás", "how are you"]):
            respuesta = texto_en_idioma(idioma_actual, {
                'es': "¡Muy bien, me alegro que estés aquí!",
                'en': "I'm doing well, glad you're here!"
            })

        elif any(x in mensaje_clean for x in ["como te llamas", "what is your name", "who are you"]):
            respuesta = texto_en_idioma(idioma_actual, {
                'es': "Soy ConversAItion, una IA creada por CrAIthon.",
                'en': "I'm ConversAItion, an AI created by CrAIthon."
            })

        elif any(x in mensaje_clean for x in ["que hora es", "what time is it"]):
            respuesta = texto_en_idioma(idioma_actual, {
                'es': "Hasta ahora no puedo ver qué hora es, pero en el futuro me van a mejorar.",
                'en': "I can't check the time right now, but I can answer questions from the web."
            })

        elif any(x in mensaje_clean for x in ["cuentame un chiste", "chiste", "tell me a joke", "joke"]):
            indice = random.randint(0, len(CHISTES) - 1)
            respuesta = CHISTES[indice]

        else:
            try:
                m_math = mensaje_clean.replace('?', '').replace('¿', '').replace('cuanto es', '').replace('cuánto es', '')
                numeros_dict = {"cero": "0", "uno": "1", "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5"}
                for palabra, numero in numeros_dict.items():
                    m_math = m_math.replace(palabra, numero)

                m_math = m_math.replace(' por ', '*').replace(' x ', '*').replace(' mas ', '+').replace(' más ', '+')
                res_math = sympify(m_math.strip())
                respuesta = texto_en_idioma(idioma_actual, {
                    'es': f"El resultado es: {round(float(res_math), 2)}",
                    'en': f"The result is: {round(float(res_math), 2)}"
                })
            except:
                try:
                    palabras_seguimiento = ["y ", "despues", "luego", "quien", "quién", "cuantos", "cuántos", "con el", "con él", "del ", "de ", "en la"]
                    ultimo_contexto = session.get('ultimo_contexto', '')

                    query_busqueda = user_input
                    if ultimo_contexto and (len(mensaje_clean) < 35 or any(p in mensaje_clean for p in palabras_seguimiento)):
                        limpio_input = user_input.replace("y quién", "quién").replace("y quien", "quien").replace("y del", "del")
                        query_busqueda = f"{ultimo_contexto} {limpio_input}"
                    else:
                        session['ultimo_contexto'] = user_input

                    respuesta_fija = respuesta_conocimiento_basico(query_busqueda, idioma_actual)
                    if respuesta_fija:
                        respuesta = respuesta_fija
                    else:
                        respuesta_web = obtener_respuesta_web(query_busqueda, idioma_actual)
                        if respuesta_web:
                            respuesta = respuesta_web['respuesta']
                            fuentes = respuesta_web['fuentes']
                        else:
                            respuesta = texto_en_idioma(idioma_actual, {
                                'es': "No he encontrado la respuesta en internet. Prueba con otra consulta o dame más detalles.",
                                'en': "I could not find the answer on the web. Try another question or give me more details."
                            })
                except Exception:
                    respuesta = texto_en_idioma(idioma_actual, {
                        'es': "Perdón, ha ocurrido un error al procesar tu solicitud.",
                        'en': "Sorry, an error occurred while processing your request."
                    })

        if respuesta:
            history.append({
                "role": "bot",
                "content": respuesta,
                "sources": fuentes if fuentes else []
            })
            guardar_historial(user_id, 'bot', respuesta)
        session['history'] = history

    return render_template_string(HTML_CHILD, history=session.get('history', []), primera_vez=primera_vez)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)