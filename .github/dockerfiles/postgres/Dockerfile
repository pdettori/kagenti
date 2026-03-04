FROM postgres:17.6@sha256:00bc86618629af00d2937fdc5a5d63db3ff8450acf52f0636ec813c7f4902929
RUN mkdir temp
RUN groupadd non-root-postgres-group
RUN useradd non-root-postgres-user --group non-root-postgres-group
RUN chown -R non-root-postgres-user:non-root-postgres-group /temp
RUN chmod 777 /temp
USER non-root-postgres