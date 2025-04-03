FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt  # --no-cache-dir is important for smaller images

COPY . .

# Expose port 5000 (Flask's default)
EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]
# Alternatively, if you don't want to use Gunicorn inside the container:
# CMD ["flask", "run", "--host=0.0.0.0"]  # Less robust, good for quick testing