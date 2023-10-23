FROM python:3-alpine
ARG VERSION

# COPY dist/ssh_mock-0.1.0-py3-none-any.whl /ssh_mock-0.1.0-py3-none-any.whl
# RUN pip install /ssh_mock-0.1.0-py3-none-any.whl

RUN pip install ssh-mock==${VERSION}


ENV HOST=0.0.0.0
WORKDIR /usr/src/app

COPY example.py example.py
ENTRYPOINT ["python", "example.py"]