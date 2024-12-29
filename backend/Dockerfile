# backend/Dockerfile

# Imagem base: Python
FROM python:3.10-slim

# Criamos um diretório de trabalho
WORKDIR /app

# Copiamos requirements e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos o resto do código
COPY . /app

# Expondo a porta que o FastAPI escuta (por exemplo 8000)
EXPOSE 8000

# Comando para rodar (usando uvicorn, por exemplo)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
