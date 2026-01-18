import json                                                                                          # Imports the library to work with JSON files (like bd.json)
import re                                                                                            # Imports the regular expressions library, used to search patterns in text
from difflib import SequenceMatcher                                                                  # Imports to compare similarity between two words
from groq import Groq                                                                                # Imports the Groq AI library to generate intelligent responses

client = Groq(api_key="Coloque sua chave aq")                                                        # Creates the Groq AI client using your API key

with open("bd.json", "r", encoding="utf-8") as f:  bd = json.load(f)                                 # Opens bd.json and loads the data into the variable bd

ultimo_assunto = None                                                                                # Stores the last topic mentioned by the user
ultimo_produto = None                                                                                # Stores the last shown product
cep_usuario = None                                                                                   # Stores the user's ZIP code to calculate shipping

SINONIMOS = {                                                                                        # Dictionary to convert similar words into one
    "camisas": "camiseta",
    "camisetas": "camiseta",
    "blusas": "camiseta",
    "tenis": "tênis",
    "sapatos": "tênis",
    "mochilas": "mochila",
    "vestidos": "vestido",
    "bones": "boné",
    "bonés": "boné",
    "calcas": "calça",
    "calças": "calça",
    "jaquetas": "jaqueta",
    "acessorios": "acessórios",
    "promoções": "promoções",
    "fretes": "frete",
    "pagamentos": "pagamento",
    "prazo": "frete",
    "entrega": "frete",
    "tempo": "frete"
}

NUMEROS = {                                                                                           # Dictionary to convert numbers written as words to integers
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10
}

def similarity(a, b):  return SequenceMatcher(None, a.lower(), b.lower()).ratio()                     # Function to compare similarity between two words, returns a number between 0 and 1

def extrair_quantidade(msg):  
    numeros = re.findall(r'\d+', msg)                                                                 # Searches for numbers in the message
    if numeros: return int(numeros[0])                                                                # Returns the first number found if any
    for palavra, valor in NUMEROS.items():                                                            # If no number found, looks for words like "two", "three"
        if palavra in msg.lower(): return valor
    return 1                                                                                          # Defaults to 1 if nothing found


def extrair_cep(msg):  
    match = re.search(r'\b\d{5}-?\d{3}\b', msg)                                                       # Searches for ZIP code in the format 12345-678 or 12345678
    if match: return match.group()                                                                    # Returns the ZIP code if found
    return None                                                                                       # Returns None if not found


def formatar_produto(produto, cores_solicitadas=None):  
    msg = f"{produto['emoji']} {produto['nome']} — R${produto['preco']:.2f}\n"                        # Puts emoji, name, and price of the product
    if 'cores' in produto:  
        cores = cores_solicitadas if cores_solicitadas else produto['cores']                          # Uses requested colors or default product colors
        msg += f"Cores disponíveis: {', '.join(cores)}\n"                                             # Adds available colors
    msg += f"Descrição: {produto['descricao']}\n"                                                     # Adds product description
    msg += "-"*40                                                                                     # Separator line
    return msg                                                                                        # Returns the formatted message


def buscar_produto_msg(msg):  
    global ultimo_produto
    msg_normalizada = msg.lower()                                                                     # Converts message to lowercase
    for palavra, substituto in SINONIMOS.items():                                                     # Normalizes synonyms
        msg_normalizada = msg_normalizada.replace(palavra, substituto)

    produtos_encontrados = []                                                                         # List to store found products

    for p in bd.get("produtos", []):                                                                  # First, searches by exact product name
        if p['nome'].lower() in msg_normalizada:
            produtos_encontrados.append(p)

    if not produtos_encontrados:                                                                      # If none found, search by category
        for p in bd.get("produtos", []):
            for cat in p.get('categorias', []):
                if cat.lower() in msg_normalizada:
                    produtos_encontrados.append(p)

    if not produtos_encontrados and ultimo_produto:                                                   # If still none found, use last shown product
        produtos_encontrados.append(ultimo_produto)

    if not produtos_encontrados:                                                                      # If nothing found
        return "Não encontrei esse produto no momento. Pode tentar outro nome ou categoria."

    produto = produtos_encontrados[0]                                                                 # Gets the first found product
    ultimo_produto = produto                                                                          # Updates last shown product
    return formatar_produto(produto)                                                                  # Returns formatted message


def detectar_intencao(msg):  
    global ultimo_assunto, ultimo_produto, cep_usuario
    msg_lower = msg.lower().strip()                                                                   # Converts to lowercase and removes spaces

    for palavra, substituto in SINONIMOS.items():                                                     # Normalizes synonyms
        msg_lower = msg_lower.replace(palavra, substituto)

    novo_cep = extrair_cep(msg_lower)                                                                 # Tries to extract ZIP code
    if novo_cep:  
        cep_usuario = novo_cep                                                                        # Saves user's ZIP
        return f"O frete para o seu endereço será calculado a partir do CEP {cep_usuario}."

    if any(p in msg_lower for p in ["suporte", "contato", "telefone", "email", "entrar em contato"]):
        return bd.get("suporte", "Não encontrei informações de contato.")

    if any(p in msg_lower for p in ["frete", "quanto tempo", "entrega", "prazo", "demora", "quanto fica", "preco do frete", "valor do frete", "calcule"]):
        if cep_usuario:  
            return f"O frete para {cep_usuario} será de R$29,90 para envio padrão 🚚. Prazo: 3–7 dias úteis."
        else:
            return "🚚 Para calcular o frete, me informe o CEP, por favor."

    if "pagamento" in msg_lower or "pix" in msg_lower or "cartão" in msg_lower:
        if "pix" in msg_lower: return bd.get("pix", bd.get("pagamento"))
        elif "cartão" in msg_lower: return bd.get("cartão", bd.get("pagamento"))
        else: return bd.get("pagamento", "Aceitamos PIX, cartão e boleto.")

    if "tabela de medidas" in msg_lower or "medidas" in msg_lower:
        return bd.get("tabela de medidas", "Não encontrei a tabela de medidas.")

    if any(p in msg_lower for p in ["troca", "devolução", "devolucoes"]):
        return bd.get("troca", "Não encontrei informações sobre troca/devolução.")

    if any(p in msg_lower for p in ["rastrear", "pedido", "codigo"]):
        return bd.get("rastrear", "Não encontrei informações sobre rastreamento.")

    if "horário" in msg_lower or "funcionamento" in msg_lower:
        return bd.get("horário", "Não encontrei informações sobre horário.")

    if any(p in msg_lower for p in ["ver produtos", "produtos", "mostrar produtos"]):
        produtos_mostrados = []
        for chave in ["camiseta","mochila","vestido","boné","calça","jaqueta","tênis","acessórios"]:
            if chave in bd:
                msg_produto = bd[chave]
                cores_chave = bd.get(f"{chave}_cores")
                if cores_chave: msg_produto += f"\nCores disponíveis: {', '.join(cores_chave)}"
                produtos_mostrados.append(msg_produto)
        return "\n\n".join(produtos_mostrados)

    if any(x in msg_lower for x in ["camiseta", "mochila", "vestido", "boné", "calça", "jaqueta", "tênis", "acessórios"]):
        produtos_mostrados = []
        for chave in ["camiseta","mochila","vestido","boné","calça","jaqueta","tênis","acessórios"]:
            if chave in msg_lower and chave in bd:
                msg_produto = bd[chave]
                cores_chave = bd.get(f"{chave}_cores")
                if cores_chave: msg_produto += f"\nCores disponíveis: {', '.join(cores_chave)}"
                produtos_mostrados.append(msg_produto)
        return "\n\n".join(produtos_mostrados)

    if "promoção" in msg_lower or "promoçoes" in msg_lower:
        return bd.get("promoções", "Não há promoções no momento.")

    return None                                                                                      # Returns None if the intention was not recognized


def resposta_groq(msg):  
    global ultimo_assunto, ultimo_produto
    produto_contexto = ultimo_produto if ultimo_produto else "nenhum produto ainda"                  # Context of the last product
    sistema = f"""
Você é o chatbot oficial da loja Lumina Style.

CONTEXTO:
- Último assunto detectado: {ultimo_assunto}
- Último produto mostrado: {produto_contexto}

REGRAS:
- Responda APENAS o que o usuário pediu.
- Entenda continuidade de conversas.
- Use dados do banco.
- Se não houver informação, responda: "Não encontrei isso no momento."
"""
    completion = client.chat.completions.create(                                                      # Creates a response using the AI
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": sistema},                                                   # Passes rules and context
            {"role": "system", "content": "Banco de dados: " + json.dumps(bd, ensure_ascii=False)},   # Passes database to the AI
            {"role": "user", "content": msg}                                                          # User message
        ],
        max_tokens=250                                                                                # Limits the number of tokens in AI response
    )
    return completion.choices[0].message.content                                                      # Returns AI response

print("🛍️ Chatbot Lumina Style iniciado!")                                                            # Shows that the chatbot has started

while True:                                                                                           # Infinite loop to chat with the user
    msg = input("\nVocê: ")                                                                           # Asks the user to type something
    if msg.lower() in ["sair", "quit", "tchau"]:                                                      # If user wants to exit
        print("Bot: Até breve! 💙")                                                                   # Says goodbye
        break                                                                                         # Exits the loop
    resposta = detectar_intencao(msg)                                                                 # Tries to detect the intention using the database
    if resposta:                                                                                      # If a response was found
        print("Bot:\n" + resposta)                                                                    # Shows the response
    else:                                                                                             # If none found
        print("Bot:\n" + resposta_groq(msg))                                                          # Uses Groq AI to respond


# --------------------- Put this in a .json file. ---------------------- # 

{
  "menu": "Aqui está o menu principal: 1. Ver produtos 2. Tabela de medidas 3. Formas de pagamento 4. Informações de frete 5. Troca e devolução 6. Rastrear pedido 7. Comprar 8. Promoções 9. Suporte e contato 10. Dúvidas gerais",
  "camiseta": "Camiseta Oversized Urban Vibes — R$79,90 👕",
  "camiseta_cores": ["Preto", "Branco", "Azul", "Vermelho"],
  "mochila": "Mochila Anti-furto Urban — R$149,90 🎒",
  "mochila_cores": ["Preto", "Azul", "Vermelho"],
  "vestido": "Vestido Midi Floral — R$119,90 👗",
  "vestido_cores": ["Rosa", "Azul", "Branco"],
  "boné": "Boné Classic Street — R$59,90 🧢",
  "boné_cores": ["Preto", "Branco", "Azul"],
  "calça": "Calça Cargo Urban — R$139,90 👖",
  "calça_cores": ["Preto", "Branco", "Azul", "Vermelho"],
  "jaqueta": "Jaqueta Corta-Vento Street — R$189,90 🧥",
  "jaqueta_cores": ["Preto", "Azul", "Vermelho"],
  "tênis": "Tênis Urban Comfort — R$199,90 👟",
  "tênis_cores": ["Preto", "Branco", "Azul", "Vermelho"],
  "acessórios": "Colares, pulseiras, brincos e anéis a partir de R$29,90 💍",
  "promoções": "🎉 Promoções do dia:\n- Camisetas: 20% OFF\n- Mochilas: Frete grátis\n- Vestidos: Leve 2 e pague 1",
  "tabela de medidas": "📏 Tabela de medidas:\nP: 165–175 cm / 55–65 kg\nM: 170–180 cm / 65–75 kg\nG: 175–185 cm / 75–85 kg\nGG: 180–195 cm / 85–100 kg",
  "cores": "Temos Preto, Branco, Azul e Vermelho 🎨",
  "cep": "Me envie seu CEP para calcular o frete 🚚",
  "frete": "🚚 Enviamos para todo o Brasil! Me diga o CEP para calcular.",
  "pagamento": "💸 Aceitamos PIX, cartão, boleto e Mercado Pago.",
  "pix": "Pagando via PIX você ganha 10% de desconto 🔥",
  "cartão": "Aceitamos Visa, MasterCard, Elo e mais 💳",
  "troca": "🔁 Trocas e devoluções em até 7 dias.",
  "rastrear": "📦 Assim que o pedido for enviado, o código aparecerá aqui no chat.",
  "suporte": "📞 Suporte 08h–18h\nEmail: suporte@luminastyle.com\nWhatsApp: (11) 99999-9999",
  "horário": "⏰ A loja funciona 24h online.",
  "estoque": "Temos sim! Me diga o produto e verifico 😄"
}


# To run the Lumina Style Chatbot, you first need to have Python 3.10 or later installed.
# Inside the project folder, it's a good idea to create a virtual environment (optional) with `python -m venv venv` and activate it (`venv\Scripts\activate` on Windows or `source venv/bin/activate` on Linux/macOS).
# Then just install the library the bot needs: `pip install groq`. You also need to have the `bd.json` file in the same folder, with the products, payments, and support.
# In the code, replace the Groq API key with your own (you can get it by creating an account at https://groq.com/).
# Then just run `python filename.py` in the terminal and the bot will start and wait for messages. To exit, just type `sair`, `quit`, or `tchau`.
