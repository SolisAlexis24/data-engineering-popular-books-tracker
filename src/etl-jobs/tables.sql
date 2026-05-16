-- Tabla compartida de metadata (un registro por ejecución del ETL)
CREATE TABLE metadata_repeticiones (
    id_metadata     SERIAL,
    fecha_registro  DATE        NOT NULL,
    conteo_semanas  INTEGER     NOT NULL,
    CONSTRAINT metadata_repeticiones_pkey PRIMARY KEY (id_metadata)
);

-- Repeticiones de libros (Top N por ejecución)
CREATE TABLE repeticiones_libros (
    id           SERIAL,
    id_metadata  INTEGER     NOT NULL,
    titulo        VARCHAR(255)      NOT NULL,
    repeticiones INTEGER     NOT NULL,
    CONSTRAINT repeticiones_libros_pkey PRIMARY KEY (id),
    CONSTRAINT repeticiones_libros_id_metadata_fkey
        FOREIGN KEY (id_metadata)
        REFERENCES metadata_repeticiones (id_metadata)
        ON DELETE CASCADE
);

-- Repeticiones de géneros (Top N por ejecución)
CREATE TABLE repeticiones_generos (
    id           SERIAL,
    id_metadata  INTEGER      NOT NULL,
    genero       VARCHAR(150) NOT NULL,
    repeticiones INTEGER      NOT NULL,
    CONSTRAINT repeticiones_generos_pkey PRIMARY KEY (id),
    CONSTRAINT repeticiones_generos_id_metadata_fkey
        FOREIGN KEY (id_metadata)
        REFERENCES metadata_repeticiones (id_metadata)
        ON DELETE CASCADE
);