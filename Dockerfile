FROM python:3.11

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install poetry

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false && poetry install --no-root

COPY .env .

COPY . .

CMD [ "poetry", "run", "python", "main.py" ]