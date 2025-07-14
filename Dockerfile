FROM python:3.13.5-slim

RUN pip install uv

WORKDIR /app

COPY . .

RUN uv pip install --system --no-cache -r requirements.txt

EXPOSE 3000

CMD ["python", "newbot2.py"]