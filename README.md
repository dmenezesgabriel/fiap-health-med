# FIAP Health&Med

This is a medical consultations system MVP made for FIAP Hackaton
Postgraduate degree in software architecture.

![archtecture](docs/archtecture.drawio.svg)

## Requirements

- Docker
- Docker Compose

## Usage

Check docker-compose.yaml to see all the services.

- **Run**:

```sh
docker compose up
```

- **Stop**:

```sh
docker compose down -v
```

## Services

### Auth Service

```sh
.
├── Dockerfile
├── __init__.py
├── main.py
├── requirements.txt
└── src
    ├── adapters
    │   └── api.py
    ├── common
    │   └── dto.py
    ├── domain
    │   ├── exceptions.py
    │   └── services
    │       └── auth_service.py
    ├── infrastructure
    │   └── database
    │       └── dynamodb_auth_repository.py
    └── ports
        └── auth_repository.py
```

### Availability Service

```sh
.
├── Dockerfile
├── __init__.py
├── main.py
├── requirements.txt
└── src
    ├── adapters
    │   └── api.py
    ├── common
    │   └── dto.py
    ├── domain
    │   └── services
    │       └── availability_service.py
    ├── infrastructure
    │   └── database
    │       └── dynamodb_availability_repository.py
    └── ports
        └── availability_repository.py
```

### Appointment Service

```sh
.
├── Dockerfile
├── main.py
├── requirements.txt
└── src
    ├── adapters
    │   └── api.py
    ├── common
    │   └── dto.py
    ├── domain
    │   └── services
    │       └── appointment_service.py
    └── infrastructure
        └── database
            └── dynamodb_appointment_repository.py
```

# Log in to Docker Hub

docker login

# Build and push Appointment Service

cd appointment_service
docker build -t dmenezesgabriel/appointment-service:v1 .
docker push dmenezesgabriel/appointment-service:v1
cd ..

# Build and push Auth Service

cd auth_service
docker build -t dmenezesgabriel/auth-service:v1 .
docker push dmenezesgabriel/auth-service:v1
cd ..

# Build and push User Service

cd user_service
docker build -t dmenezesgabriel/availability-service:v1 .
docker push dmenezesgabriel/availability-service:v1
cd ..
