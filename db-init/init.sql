CREATE TABLE usuario(
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(50) NULL,
    telefono VARCHAR(15) UNIQUE NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE
);
CREATE TABLE rol(
    id BIGSERIAL PRIMARY KEY,
    descripcion VARCHAR(50) NOT NULL
);
CREATE TABLE usuario_rol(
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT NOT NULL,
    rol_id BIGINT NOT NULL,
    UNIQUE (usuario_id, rol_id)
);

INSERT INTO usuario (username, password, nombre, telefono, correo) VALUES ('shawdog','pbkdf2_sha256$1200000$Okg6cOJr9FRpvrJtkwM7PL$ZSMKTthy/5kT/THVq986v/H9E3u1iifFUEHV0rXjVvM=','Admin','5512345678','admin@example.com');
INSERT INTO rol (descripcion) VALUES ('ROLE_RECLUTADOR'),('ROLE_ASPIRANTE'),('ROLE_ADMIN');
INSERT INTO usuario_rol (usuario_id, rol_id) VALUES (1,3),(1,2),(1,1);