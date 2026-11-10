from flask import Flask, render_template_string, request, session, url_for
import random
import os
import logging
import time
import unicodedata
import sympy
from sympy import sympify
import sqlite3
import uuid
import requests
from bs4 import BeautifulSoup
from xml.etree import ElementTree
try:
    from duckduckgo_search import DDGS
except ModuleNotFoundError:
    DDGS = None
from datetime import datetime
import re
from langdetect import detect

logger = logging.getLogger(__name__)

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

    texto_norm = unicodedata.normalize('NFKD', texto.lower())
    texto_norm = ''.join(
        caracter for caracter in texto_norm
        if not unicodedata.combining(caracter)
    )
    texto_norm = re.sub(r'[^a-zA-Z\s]', ' ', texto_norm)
    texto_norm = re.sub(r'\s+', ' ', texto_norm).strip()

    if not texto_norm:
        return 'es'

    spanish_markers = [
        'hola', 'buenas', 'buenos', 'adios', 'gracias', 'por favor', 'ayuda',
        'como', 'que', 'cuanto', 'quien', 'donde', 'cual', 'mi nombre',
        'chiste', 'resultado', 'sabes', 'llamas', 'llamo', 'hoy', 'te llamas',
        'cuentame', 'yo soy', 'dime', 'puedes', 'podrias', 'explicame',
        'contarme', 'quiero saber'
    ]
    english_markers = [
        'hello', 'hi', 'hey', 'goodbye', 'bye', 'thanks', 'please', 'help', 'how are you',
        'what', 'where', 'who', 'my name is', 'who are you', 'what is your name', 'what time',
        'tell me a joke', 'joke', 'do you like python', 'where are you'
    ]

    if any(re.search(rf'\b{re.escape(marker)}\b', texto_norm) for marker in spanish_markers):
        return 'es'
    if any(re.search(rf'\b{re.escape(marker)}\b', texto_norm) for marker in english_markers):
        return 'en'

    palabras = set(re.findall(r'\b[a-z]+\b', texto_norm))
    marcadores_espanol = {
        'al', 'como', 'con', 'cual', 'cuando', 'cuanto', 'del', 'desde', 'es',
        'fue', 'hasta', 'muy', 'pero', 'por', 'para', 'que', 'quien', 'son',
        'tambien', 'una', 'un', 'y', 'dime', 'puedes', 'podrias', 'quiero',
        'sabes', 'explicame', 'contarme'
    }
    marcadores_ingles = {
        'a', 'an', 'and', 'are', 'can', 'could', 'did', 'do', 'does', 'for',
        'from', 'have', 'how', 'in', 'is', 'it', 'of', 'on', 'or', 'the', 'to',
        'were', 'what', 'when', 'where', 'which', 'who', 'why', 'with'
    }
    coincidencias_espanol = len(palabras & marcadores_espanol)
    coincidencias_ingles = len(palabras & marcadores_ingles)
    if coincidencias_espanol > coincidencias_ingles:
        return 'es'
    if coincidencias_ingles > coincidencias_espanol:
        return 'en'

    if len(palabras) < 4:
        return 'es'

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
        return 'es'
    except Exception:
        return 'es'


def texto_en_idioma(idioma, textos):
    return textos.get(idioma) or textos.get('es') or next(iter(textos.values()))


def respuesta_conocimiento_basico(query, idioma):
    q = (query or '').lower().strip()
    consulta_simple = normalizar_consulta_web(q)
    if consulta_simple == 'java':
        respuesta = texto_en_idioma(idioma, {
            'es': 'Java es un lenguaje de programación orientado a objetos muy usado en empresas, aplicaciones empresariales y Android.',
            'en': 'Java is a popular object-oriented programming language used in enterprise software, backend development, and Android apps.'
        })
        return {
            'respuesta': respuesta,
            'fuentes': [{
                'titulo': 'Java — sitio oficial',
                'url': 'https://www.java.com/',
                'snippet': 'Sitio oficial de Java.'
            }]
        }
    if consulta_simple == 'python':
        respuesta = texto_en_idioma(idioma, {
            'es': 'Python es un lenguaje de programación muy popular por su simplicidad, legibilidad y uso en IA, automatización y desarrollo web.',
            'en': 'Python is a very popular programming language thanks to its simplicity, readability, and use in AI, automation, and web development.'
        })
        return {
            'respuesta': respuesta,
            'fuentes': [{
                'titulo': 'Python.org — acerca de Python',
                'url': 'https://www.python.org/about/',
                'snippet': 'Información oficial sobre el lenguaje de programación Python.'
            }]
        }
    return None


def resumir_texto(texto):
    texto = re.sub(r'\s+', ' ', (texto or '').replace('\u200b', '').replace('\ufeff', '')).strip()
    if not texto:
        return ''

    texto = re.sub(r'\b(ver m\u00e1s|leer m\u00e1s|descargar|enlace|hace \d+ d\u00edas)\b', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return re.sub(r'^(Titulo|Title|Resumen)\s*[:\-]\s*', '', texto, flags=re.IGNORECASE)


def resultado_relevante(query, titulo, cuerpo):
    return puntuar_resultado(query, titulo, cuerpo) >= 0.24


PALABRAS_VACIAS_BUSQUEDA = {
    'a', 'al', 'algo', 'and', 'are', 'as', 'at', 'about', 'can', 'con', 'cual',
    'cuales', 'cuando', 'cuanto', 'cuanta', 'cuantos', 'cuantas', 'como', 'de', 'del',
    'dime', 'do', 'does', 'doing', 'el', 'ella', 'ellas', 'ellos', 'en', 'es',
    'donde', 'explica', 'explicame', 'explicar', 'esta', 'estan', 'estaba', 'estaban',
    'estuve', 'estuvo', 'favor', 'for', 'fue', 'fueron', 'ha',
    'hace', 'han', 'has', 'have', 'having', 'hay', 'how', 'i', 'in', 'is',
    'la', 'las', 'le', 'les', 'lo', 'los', 'me', 'mi', 'mis', 'my', 'of', 'o',
    'or', 'para', 'please', 'por', 'podria', 'podrias', 'puede', 'pueden',
    'puedes', 'que', 'quien', 'quienes', 'quisiera', 'saber', 'se', 'sobre',
    'tell', 'the', 'to', 'un', 'una', 'unas', 'uno', 'unos', 'was', 'we',
    'what', 'when', 'where', 'which', 'who', 'why', 'with', 'would', 'you',
    'your', 'y', 'contarme', 'cuentame', 'decirme', 'explicame', 'quiero'
}


def tokens_busqueda(texto):
    normalizado = unicodedata.normalize('NFKD', (texto or '').lower())
    normalizado = ''.join(
        caracter for caracter in normalizado
        if not unicodedata.combining(caracter)
    )
    return re.findall(r'\w+', normalizado)


def tipo_pregunta(query):
    texto = ' '.join(tokens_busqueda(query))
    patrones = {
        'who': r'\b(?:who|whom|whose|quien|quienes)\b',
        'when': r'\b(?:when|cuando|fecha|date|year|ano)\b',
        'where': r'\b(?:where|donde|ubicacion|location)\b',
        'why': r'\b(?:why|porque|por que|razon|motivo)\b',
        'how': r'\b(?:how|como funciona|como se|how does|how do|how is)\b',
        'what': r'\b(?:what|que es|que son|define|meaning)\b'
    }
    return next(
        (tipo for tipo, patron in patrones.items() if re.search(patron, texto)),
        None
    )


PATRONES_EVIDENCIA_PREGUNTA = {
    'who': (
        r'\b(?:was|is|became|born|discovered|invented|founded|served|won|identified|'
        r'fue|es|nacio|descubrio|invento|fundo|gano|identifico)\b',
    ),
    'when': (
        r'\b(?:1[5-9]\d{2}|20\d{2}|21\d{2})\b',
        r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december|'
        r'enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b'
    ),
    'where': (
        r'\b(?:(?:is|are|was|were)\s+)?(?:located|situated|based|stands|lies)\s+(?:in|at|near)\s+[a-z][\w-]*\b',
        r'\b(?:is|are|was|were)\s+(?:in|at|near)\s+[a-z][\w-]*\b',
        r'\b(?:esta|estan|ubicad[oa]s?|situad[oa]s?|se encuentra|se ubica)\s+(?:en|cerca de)\s+[a-z][\w-]*\b',
        r'\b(?:built|constructed|erected)\s+(?:in|on|at)\s+[a-z][\w-]*\b',
        r'\b(?:construid[oa]s?|erigida?|levantad[oa]s?)\s+(?:en|sobre)\s+[a-z][\w-]*\b'
    ),
    'why': (
        r'\b(?:because|since|due to|as a result|therefore|porque|ya que|debido a|por eso|se debe a)\b',
    ),
    'how': (
        r'\b(?:by|through|use|uses|using|via|process|method|steps|mediante|a traves|utiliza|utilizan|'
        r'utilizando|proceso|metodo|pasos|funciona|se realiza|se produce)\b',
    ),
    'what': (
        r'\b(?:is(?:\s+(?:a|an|the))?|are(?:\s+(?:a|an|the))?|means|refers to|defined as|consists? of|'
        r'es(?: un[oa]?)?|son(?: un[oa]?)?|significa|se define como|consiste en|se refiere a)\b',
    )
}


PALABRAS_ACCION_PREGUNTA = {
    'who': {'became', 'born', 'descubierta', 'descubierto', 'descubrio', 'discovered', 'founded', 'fue', 'gano', 'identified', 'invented', 'is', 'nacio', 'was', 'won'},
    'when': {'built', 'completed', 'created', 'founded', 'happened', 'opened', 'published', 'released', 'started'},
    'where': {'based', 'located', 'lies', 'situated', 'stands', 'ubicada', 'ubicado'},
    'how': {'function', 'functions', 'funciona', 'operate', 'operates', 'work', 'works'},
    'what': {'define', 'defined', 'meaning', 'means'}
}


def tema_busqueda(query):
    terminos = normalizar_consulta_web(query).split()
    acciones = PALABRAS_ACCION_PREGUNTA.get(tipo_pregunta(query), set())
    return [termino for termino in terminos if termino not in acciones]


def puntuar_titulo_tema(query, titulo):
    tema = tema_busqueda(query)
    sufijos_editoriales = {'wikipedia', 'enciclopedia', 'libre'}
    titulo_tokens = [
        token for token in tokens_busqueda(titulo)
        if token not in PALABRAS_VACIAS_BUSQUEDA and token not in sufijos_editoriales
    ]
    if not tema or not titulo_tokens:
        return 0.0

    def coincide(termino, token):
        return token == termino or (
            len(os.path.commonprefix((termino, token))) >= 6
            and len(os.path.commonprefix((termino, token))) / min(len(termino), len(token)) >= 0.65
        )

    for inicio in range(len(titulo_tokens) - len(tema) + 1):
        if all(
            coincide(termino, token)
            for termino, token in zip(tema, titulo_tokens[inicio:inicio + len(tema)])
        ):
            extras = len(titulo_tokens) - len(tema)
            if inicio == 0 and extras == 0:
                return 1.5
            return 0.65 - min(0.9, extras * 0.35)

    coincide_tema = all(any(coincide(termino, token) for token in titulo_tokens) for termino in tema)
    if coincide_tema:
        return -0.45

    return 0.0


def frase_responde_pregunta(query, titulo, frase):
    intent = tipo_pregunta(query)
    if intent not in PATRONES_EVIDENCIA_PREGUNTA:
        return False

    frase_normalizada = ' '.join(tokens_busqueda(frase))
    evidencia = any(
        re.search(patron, frase_normalizada, flags=re.IGNORECASE)
        for patron in PATRONES_EVIDENCIA_PREGUNTA[intent]
    )
    if intent == 'who':
        nombre_en_frase = bool(re.search(r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b', frase))
        nombre_en_titulo = bool(
            re.fullmatch(r'(?:Sir\s+)?[A-Z][a-z]+\s+[A-Z][a-z]+', titulo or '')
        )
        evidencia = evidencia and (nombre_en_frase or nombre_en_titulo)
    elif intent == 'where':
        evidencia = evidencia or bool(re.search(
            r'\b(?:in|at|on|near|en|sobre|cerca de)\s+'
            r'(?:(?:the|el|la|los|las)\s+)?[A-Z\u00c0-\u00de][\w-]*',
            frase
        ))
    return evidencia


def puntuar_resultado(query, titulo, cuerpo):
    terminos_ordenados = tema_busqueda(query)
    terminos = set(terminos_ordenados)
    if not terminos:
        return 1.0

    tokens_titulo = set(tokens_busqueda(titulo))
    tokens_cuerpo = set(tokens_busqueda(cuerpo))
    tokens_texto = tokens_titulo | tokens_cuerpo
    numeros = {termino for termino in terminos if termino.isdigit()}
    if not numeros.issubset(tokens_texto):
        return 0.0

    puntuacion = 0.0
    coincidencias = 0
    for termino in terminos:
        if termino in tokens_titulo:
            puntuacion += 1.0
            coincidencias += 1
            continue
        if termino in tokens_cuerpo:
            puntuacion += 0.7
            coincidencias += 1
            continue

        prefijos = [
            token for token in tokens_texto
            if len(os.path.commonprefix((termino, token))) >= 6
            and len(os.path.commonprefix((termino, token))) / min(len(termino), len(token)) >= 0.65
        ]
        if prefijos:
            mejor_prefijo = max(
                prefijos,
                key=lambda token: len(os.path.commonprefix((termino, token))) / max(len(termino), len(token))
            )
            puntuacion += 0.8 if mejor_prefijo in tokens_titulo else 0.52
            coincidencias += 1

    if len(terminos) > 1 and coincidencias < 2:
        return 0.0

    puntuacion /= len(terminos)

    titulo_normalizado = [
        token for token in tokens_busqueda(titulo)
        if token not in PALABRAS_VACIAS_BUSQUEDA
    ]
    posiciones = []
    inicio = 0
    for termino in terminos_ordenados:
        for posicion in range(inicio, len(titulo_normalizado)):
            token = titulo_normalizado[posicion]
            coincidencia = token == termino or (
                len(os.path.commonprefix((termino, token))) >= 6
                and len(os.path.commonprefix((termino, token))) / min(len(termino), len(token)) >= 0.65
            )
            if coincidencia:
                posiciones.append(posicion)
                inicio = posicion + 1
                break

    if len(posiciones) > 1:
        distancia = posiciones[-1] - posiciones[0]
        puntuacion += 0.35 / distancia

    return puntuacion


def puntuar_frase_respuesta(query, titulo, frase):
    if '?' in frase or '¿' in frase:
        return -1.2

    puntuacion = puntuar_resultado(query, titulo, frase)
    intent = tipo_pregunta(query)
    palabras_consulta = set(tokens_busqueda(query))
    pregunta_quien = bool(palabras_consulta & {'who', 'quien'})
    pregunta_descubrimiento = bool(
        palabras_consulta
        & {'discover', 'discovered', 'discovery', 'descubrio', 'descubierta', 'descubierto'}
    )
    palabras_frase = set(tokens_busqueda(frase))
    acciones_descubrimiento = {
        'demonstrate', 'demonstrated', 'descubrio', 'descubierta', 'descubierto',
        'discovered', 'discovery', 'first', 'found', 'identified', 'invented',
        'named', 'show', 'showed'
    }
    nombre_en_frase = any(
        coincidencia.start() > 0
        for coincidencia in re.finditer(r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b', frase)
    )

    if (
        pregunta_quien
        and pregunta_descubrimiento
        and palabras_frase & acciones_descubrimiento
        and (nombre_en_frase or frase_responde_pregunta(query, titulo, frase))
    ):
        puntuacion += 1.5 if nombre_en_frase else 0.5

    if intent in PATRONES_EVIDENCIA_PREGUNTA:
        puntuacion += 0.9 if frase_responde_pregunta(query, titulo, frase) else -1.2
    return puntuacion


def resumir_resultado(query, cuerpo, titulo=''):
    cuerpo = re.sub(
        r'\s+',
        ' ',
        (cuerpo or '').replace('\u200b', '').replace('\ufeff', '')
    ).strip()
    frases = [
        frase.strip()
        for frase in re.split(r'(?<=[.!?])\s+', cuerpo or '')
        if frase.strip()
    ]
    terminos_pregunta = set(tema_busqueda(query))
    frases_relevantes = sorted(
        (
            (puntuar_frase_respuesta(query, titulo, frase), indice, frase)
            for indice, frase in enumerate(frases)
        ),
        key=lambda item: (-item[0], item[1])
    )
    seleccionadas = []
    terminos_cubiertos = set(tokens_busqueda(titulo))
    pendientes = set(terminos_pregunta)
    for puntuacion, indice, frase in frases_relevantes:
        if puntuacion < 0.24:
            break
        tokens_frase = set(tokens_busqueda(frase))
        nuevos_terminos = set()
        for termino in pendientes:
            for token in terminos_cubiertos | tokens_frase:
                prefijo_comun = os.path.commonprefix((termino, token))
                if token == termino or (
                    len(prefijo_comun) >= 6
                    and len(prefijo_comun) / min(len(termino), len(token)) >= 0.65
                ):
                    nuevos_terminos.add(termino)
                    break
        if nuevos_terminos or not seleccionadas:
            seleccionadas.append((indice, frase))
            pendientes.difference_update(nuevos_terminos)
        if not pendientes:
            break

    if pendientes:
        return ''
    seleccionadas = [
        frase for _, frase in sorted(seleccionadas)
    ]
    if not seleccionadas:
        return ''
    texto = ' '.join(seleccionadas)
    palabras_consulta = set(tokens_busqueda(query))
    if palabras_consulta & {'who', 'quien'} and palabras_consulta & {
        'discover', 'discovered', 'discovery', 'descubrio', 'descubierta', 'descubierto'
    }:
        texto = re.split(
            r'\s+(?:however|but|although|sin\s+embargo|pero|aunque)\b',
            texto,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0].strip(' ,;:')

    tokens_titulo = set(tokens_busqueda(titulo))
    intent = tipo_pregunta(query)
    titulo_persona = bool(
        intent == 'who'
        and re.fullmatch(r'(?:Sir\s+)?[A-Z][a-z]+\s+[A-Z][a-z]+', titulo or '')
    )
    if texto and titulo_persona and not tokens_titulo.intersection(tokens_busqueda(texto)):
        texto = f"{titulo}: {texto}"
    resumen = resumir_texto(texto)
    return resumen if not resumen or resumen[-1] in '.!?' else resumen + '.'


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


class ErrorBusquedaWeb(Exception):
    pass


WIKIPEDIA_CACHE_SECONDS = 300
WIKIPEDIA_CACHE_LIMIT = 256
wikipedia_cache = {}


def normalizar_consulta_web(query):
    terminos = [
        termino for termino in tokens_busqueda(query)
        if termino not in PALABRAS_VACIAS_BUSQUEDA
    ]
    return ' '.join(terminos) or (query or '').strip()


def consultas_alternativas_web(query):
    terminos = normalizar_consulta_web(query).split()
    alternativas = []
    for cantidad in range(1, min(3, len(terminos) - 1) + 1):
        alternativa = ' '.join(terminos[cantidad:])
        if alternativa and alternativa not in alternativas:
            alternativas.append(alternativa)
    if query and query.strip() not in alternativas:
        alternativas.append(query.strip())
    return alternativas


def buscar_duckduckgo(query, idioma):
    if DDGS is None:
        raise ErrorBusquedaWeb("No está instalada la dependencia duckduckgo-search.")

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

        with DDGS(timeout=10) as ddgs:
            resultados = list(ddgs.text(
                keywords=query,
                region=codigo_region,
                safesearch='moderate',
                max_results=8,
                backend='auto'
            ))
        return resultados
    except Exception as error:
        logger.exception("No se pudo realizar la búsqueda web en DuckDuckGo.")
        raise ErrorBusquedaWeb("DuckDuckGo no está disponible temporalmente.") from error


def buscar_bing(query, idioma):
    regiones = {
        'de': ('DE', 'de'),
        'en': ('US', 'en'),
        'es': ('ES', 'es'),
        'fr': ('FR', 'fr'),
        'pt': ('BR', 'pt')
    }
    region, idioma_busqueda = regiones.get(idioma, ('US', 'en'))

    try:
        respuesta = requests.get(
            'https://www.bing.com/search',
            params={
                'format': 'rss',
                'q': query,
                'cc': region,
                'setlang': idioma_busqueda
            },
            headers={'User-Agent': 'Mozilla/5.0 (compatible; ConversAItion/0.3)'},
            timeout=8
        )
        respuesta.raise_for_status()
        raiz = ElementTree.fromstring(respuesta.content)
    except (requests.RequestException, ElementTree.ParseError) as error:
        logger.exception("No se pudo realizar la búsqueda web en Bing.")
        raise ErrorBusquedaWeb("Bing no está disponible temporalmente.") from error

    return [
        {
            'title': elemento.findtext('title', default='').strip(),
            'body': elemento.findtext('description', default='').strip(),
            'href': elemento.findtext('link', default='').strip()
        }
        for elemento in raiz.findall('./channel/item')
        if elemento.findtext('title') or elemento.findtext('description')
    ]


def buscar_wikipedia(query, idioma):
    clave_cache = (query, idioma)
    momento = time.monotonic()
    entrada_cache = wikipedia_cache.get(clave_cache)
    if entrada_cache and momento - entrada_cache[0] < WIKIPEDIA_CACHE_SECONDS:
        return [dict(pagina) for pagina in entrada_cache[1]]

    codigo_idioma = idioma if re.fullmatch(r'[a-z]{2,3}', idioma or '') else 'en'
    url = f"https://{codigo_idioma}.wikipedia.org/w/api.php"
    parametros = {
        'action': 'query',
        'generator': 'search',
        'gsrsearch': query,
        'gsrlimit': 6,
        'prop': 'extracts|info',
        'exintro': 1,
        'explaintext': 1,
        'exchars': 1200,
        'inprop': 'url',
        'format': 'json',
        'formatversion': 2
    }

    try:
        respuesta = requests.get(
            url,
            params=parametros,
            headers={'User-Agent': 'ConversAItion/0.3'},
            timeout=8
        )
        respuesta.raise_for_status()
        paginas = respuesta.json().get('query', {}).get('pages', [])
    except (requests.RequestException, ValueError) as error:
        logger.exception("No se pudo realizar la búsqueda de respaldo en Wikipedia.")
        raise ErrorBusquedaWeb("Wikipedia no está disponible temporalmente.") from error

    if isinstance(paginas, dict):
        paginas = list(paginas.values())

    resultados = [
        {
            'title': pagina.get('title', ''),
            'body': pagina.get('extract', ''),
            'href': pagina.get('fullurl', '')
        }
        for pagina in paginas
        if pagina.get('title') and pagina.get('extract')
    ]
    wikipedia_cache[clave_cache] = (momento, resultados)
    if len(wikipedia_cache) > WIKIPEDIA_CACHE_LIMIT:
        clave_mas_antigua = min(wikipedia_cache, key=lambda clave: wikipedia_cache[clave][0])
        del wikipedia_cache[clave_mas_antigua]
    return [dict(pagina) for pagina in resultados]


def procesar_resultados_busqueda(query, resultados):
    candidatos = []
    urls_vistas = set()

    for resultado in resultados:
        if not isinstance(resultado, dict):
            continue

        titulo = (resultado.get('title') or '').strip()
        cuerpo = (resultado.get('body') or '').strip()
        enlace = (
            resultado.get('href') or resultado.get('url') or resultado.get('link') or ''
        ).strip()

        if not titulo and not cuerpo:
            continue
        if set(tokens_busqueda(titulo)) & {'disambiguation', 'desambiguacion'}:
            continue

        if enlace and not re.match(r'^https?://[^/\s]+(?:/|$)', enlace, flags=re.IGNORECASE):
            enlace = ''
        if not enlace:
            continue

        puntuacion = puntuar_resultado(query, titulo, cuerpo)
        if puntuacion < 0.24:
            continue

        if enlace and len(cuerpo) < 120:
            html = descargar_web(enlace)
            if html:
                texto_limpio = limpiar_html(html)
                if texto_limpio:
                    cuerpo = texto_limpio

        if not cuerpo or any(
            fragmento in cuerpo.lower()
            for fragmento in ("search settings", "loc. pronom", "yuasa", "skincare")
        ):
            continue

        puntuacion = puntuar_resultado(query, titulo, cuerpo)
        if puntuacion < 0.24:
            continue

        resumen = resumir_resultado(query, cuerpo, titulo=titulo)
        if not resumen:
            continue
        puntuacion += puntuar_titulo_tema(query, titulo)
        if tipo_pregunta(query) in PATRONES_EVIDENCIA_PREGUNTA:
            puntuacion += 1.0 if frase_responde_pregunta(query, titulo, resumen) else -0.8

        if enlace:
            if enlace in urls_vistas:
                continue
            else:
                urls_vistas.add(enlace)

        candidatos.append({
            'puntuacion': puntuacion,
            'respuesta': resumen,
            'fuente': {
                'titulo': titulo or 'Fuente web',
                'url': enlace,
                'snippet': cuerpo[:180]
            }
        })

    return sorted(candidatos, key=lambda candidato: candidato['puntuacion'], reverse=True)


def obtener_respuesta_web(query, idioma):
    consulta_busqueda = normalizar_consulta_web(query)
    consulta_tema = ' '.join(tema_busqueda(query)).strip() or consulta_busqueda
    consultas = []
    for proveedor, consulta in (
        (buscar_bing, query.strip()),
        (buscar_bing, consulta_tema),
        (buscar_wikipedia, query.strip()),
        (buscar_wikipedia, consulta_tema)
    ):
        clave = (proveedor, consulta)
        if consulta and clave not in consultas:
            consultas.append(clave)

    proveedores_fallidos = set()
    candidatos = []
    wikipedia_fallido = False

    for proveedor, consulta in consultas:
        if proveedor in proveedores_fallidos:
            continue
        try:
            resultados = proveedor(consulta, idioma)
        except ErrorBusquedaWeb as error:
            logger.warning("Proveedor de búsqueda %s no disponible: %s", proveedor.__name__, error)
            proveedores_fallidos.add(proveedor)
            if proveedor is buscar_wikipedia:
                wikipedia_fallido = True
            continue

        candidatos.extend(procesar_resultados_busqueda(query, resultados or []))

    if not candidatos:
        for consulta in dict.fromkeys((query.strip(), consulta_tema)):
            try:
                resultados = buscar_duckduckgo(consulta, idioma)
            except ErrorBusquedaWeb as error:
                logger.warning("Proveedor de búsqueda %s no disponible: %s", buscar_duckduckgo.__name__, error)
                proveedores_fallidos.add(buscar_duckduckgo)
                break
            candidatos.extend(procesar_resultados_busqueda(query, resultados or []))
            if candidatos:
                break

    if not candidatos and not wikipedia_fallido:
        for consulta_alternativa in consultas_alternativas_web(query):
            if consulta_alternativa == query.strip():
                continue
            try:
                resultados = buscar_wikipedia(consulta_alternativa, idioma)
            except ErrorBusquedaWeb as error:
                logger.warning("Búsqueda alternativa de Wikipedia no disponible: %s", error)
                proveedores_fallidos.add(buscar_wikipedia)
                continue
            candidatos = procesar_resultados_busqueda(query, resultados)
            if candidatos:
                break

    candidatos.sort(key=lambda candidato: candidato['puntuacion'], reverse=True)

    if not candidatos:
        if len(proveedores_fallidos) == 3:
            raise ErrorBusquedaWeb("Los servicios de búsqueda no están disponibles.")
        return None

    mejores = []
    for candidato in candidatos:
        tokens_respuesta = set(tokens_busqueda(candidato['respuesta']))
        duplicada = False
        for mejor in mejores:
            tokens_mejor = set(tokens_busqueda(mejor['respuesta']))
            tokens_combinados = tokens_respuesta | tokens_mejor
            if tokens_combinados and len(tokens_respuesta & tokens_mejor) / len(tokens_combinados) >= 0.7:
                duplicada = True
                break

        if duplicada:
            continue
        mejores.append(candidato)
        if len(mejores) == 2:
            break

    respuesta = mejores[0]['respuesta']
    fuente_principal = mejores[0]['fuente']

    return {
        'respuesta': respuesta,
        'fuentes': [fuente_principal]
    }

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
    <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
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

        .brand-logo {
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            width: clamp(90px, 10vw, 140px);
            height: auto;
            object-fit: contain;
        }

        .brand-title {
            width: clamp(180px, 30vw, 340px);
            height: 110px;
            object-fit: contain;
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

        .source-list {
            align-self: flex-start;
            max-width: min(84%, 700px);
            display: flex;
            flex-wrap: wrap;
            gap: 8px 12px;
            padding: 0 8px;
            color: var(--muted);
            font-size: 0.8rem;
        }

        .source-list a {
            color: var(--accent);
            overflow-wrap: anywhere;
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
        }

        @media (max-width: 576px) {
            .topbar {
                padding: 18px 12px 12px;
            }
            .brand-wrap {
                min-height: 68px;
            }
            .brand-logo {
                width: 48px;
                left: 0;
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
                width: min(42vw, 180px);
                height: 76px;
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
                <img class="brand-logo" src="{{ url_for('static', filename='logo_ia.png') }}" alt="Logo IA">
                <img class="brand-title" src="{{ url_for('static', filename='ConversAItion.png') }}" alt="ConversAItion">
                <div class="beta-tag">
                    <div class="beta-orbit"></div>
                    <div class="beta-pill">0.3 BETA</div>
                </div>
            </div>
        </header>

        <main class="chat-panel" id="chat">
            {% for msg in history %}
                <div class="msg {{ msg.role }}">{{ msg.content }}</div>
                {% if msg.sources %}
                    <div class="source-list">
                        <span>{{ msg.source_label or 'Fuentes' }}:</span>
                        {% for source in msg.sources %}
                            <a href="{{ source.url }}" target="_blank" rel="noopener noreferrer" title="{{ source.snippet }}">{{ source.titulo }}</a>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endfor %}
        </main>

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

        elif re.search(r'\b(?:hola|buenas|moin|hello|hi|hey)\b', mensaje_clean):
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

        elif re.search(r'\b(?:adiós|adios|goodbye|bye)\b', mensaje_clean):
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
                m_math = mensaje_clean.replace('?', '').replace('¿', '')
                m_math = re.sub(r'^(?:cu[aá]nto es|what is|calculate|calcula)\s+', '', m_math)
                numeros_dict = {"cero": "0", "uno": "1", "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5"}
                for palabra, numero in numeros_dict.items():
                    m_math = re.sub(rf'\b{palabra}\b', numero, m_math)

                m_math = re.sub(r'\bpor\b|\bx\b', '*', m_math)
                m_math = re.sub(r'\b(?:mas|más)\b', '+', m_math)
                m_math = re.sub(r'\bmenos\b', '-', m_math)
                m_math = re.sub(r'\b(?:dividido entre|divided by)\b', '/', m_math)
                if not re.search(r'\d', m_math) or not re.fullmatch(r'[\d\s.+\-*/()%]+', m_math):
                    raise ValueError("La consulta no es una expresión matemática.")

                res_math = sympify(m_math.strip())
                if not res_math.is_number or res_math.free_symbols:
                    raise ValueError("La consulta no se pudo evaluar como una expresión numérica.")
                respuesta = texto_en_idioma(idioma_actual, {
                    'es': f"El resultado es: {round(float(res_math), 2)}",
                    'en': f"The result is: {round(float(res_math), 2)}"
                })
            except:
                try:
                    palabras_seguimiento = [
                        "y ", "despues", "después", "luego", "quien", "quién",
                        "cuantos", "cuántos", "con el", "con él", "del ", "de ", "en la",
                        "and who", "and when", "and where", "and what", "and how",
                        "what about", "how about", "after that"
                    ]
                    ultimo_contexto = session.get('ultimo_contexto', '')

                    query_busqueda = user_input
                    es_seguimiento = mensaje_clean.startswith("y ") or any(
                        p != "y " and p in mensaje_clean for p in palabras_seguimiento
                    )
                    if ultimo_contexto and es_seguimiento:
                        limpio_input = user_input.replace("y quién", "quién").replace("y quien", "quien").replace("y del", "del")
                        query_busqueda = f"{ultimo_contexto} {limpio_input}"
                    else:
                        session['ultimo_contexto'] = user_input

                    respuesta_fija = respuesta_conocimiento_basico(query_busqueda, idioma_actual)
                    if respuesta_fija:
                        respuesta = respuesta_fija['respuesta']
                        fuentes = respuesta_fija['fuentes']
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
                except ErrorBusquedaWeb:
                    respuesta = texto_en_idioma(idioma_actual, {
                        'es': "No he podido conectar con el buscador ahora mismo. Inténtalo de nuevo más tarde.",
                        'en': "I could not connect to the search service right now. Please try again later."
                    })
                except Exception:
                    logger.exception("Error al procesar la consulta del usuario.")
                    respuesta = texto_en_idioma(idioma_actual, {
                        'es': "Perdón, ha ocurrido un error al procesar tu solicitud.",
                        'en': "Sorry, an error occurred while processing your request."
                    })

        if respuesta:
            history.append({
                "role": "bot",
                "content": respuesta,
                "sources": fuentes if fuentes else [],
                "source_label": "Fuentes" if idioma_actual == 'es' else "Sources"
            })
            guardar_historial(user_id, 'bot', respuesta)
        session['history'] = history

    return render_template_string(HTML_CHILD, history=session.get('history', []), primera_vez=primera_vez)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)