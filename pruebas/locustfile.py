"""
locustfile.py - Pruebas de carga de CaribeShop (P1 y P2).

Tiene 3 modos

1) P1.1 Capacidad de una instancia (autoscale min = max = 1)
   Repetir subiendo -u hasta que el p95 supere 1 segundo:

   locust -f locustfile.py --headless -u 50 -r 5 -t 5m --host http://<IP_LB> `
          --csv evidencias/p1-capacidad/u50 --html evidencias/p1-capacidad/u50.html

2) P1.2 Perfil escalonado de al menos 25 min (autoscale restaurado)
   PICO = usuarios del escalón alto.
   
   $env:PERFIL = "escalonado"; $env:PICO = "200"
   locust -f locustfile.py --headless --host http://<IP_LB> `
          --csv evidencias/p1-escalonada/run --html evidencias/p1-escalonada/run.html
    
    Para volver al modo normal se debe realizar Remove-Item Env:PERFIL

3) P2 Carga moderada constante durante las pruebas de falla
   locust -f locustfile.py --headless -u 60 -r 5 -t 10m --host http://<IP_LB> `
          --csv evidencias/p2-fallas/falla --html evidencias/p2-fallas/falla.html

Con --csv se genera <prefijo>_stats_history.csv (RPS, p95 y fallos por
segundo), la base para los graficos alineados de P1.3 y para medir el 
porcentaje de error en P2.

Dependencias: pip install locust
"""
import os

from locust import HttpUser, LoadTestShape, between, task

# Timeout corto: en una falla abrupta una petición colgada, se corta y cuenta como falla
# No debe quedar colgada esperando minutos
TIMEOUT_S = 5

# HttpUser agrega un atributo del cliente que es utilizado para hacer HTTP requests.


class Visitante(HttpUser):
    """ Visitante en la tienda """

    # Pausa entre una acción y la siguiente
    wait_time = between(0.5, 1.5)

    # 10 acciones van a la página principal por cada 1 a health_check
    @task(10)
    def principal_page(self):
        self.client.get("/", name="/", timeout=TIMEOUT_S)

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health", timeout=TIMEOUT_S)


# Para que locust no ignore -u y -r siempre
if os.getenv("PERFIL") == "escalonado":

    # Perfil escalonado (subida, carga sostenida, bajada)
    # Usuarios del escalón alto, 200 por defecto
    PICO = int(os.getenv("PICO", 200))
    BASE = max(5, int(PICO*0.15))  # El 15% del pico, con un mínimo de 5
    MEDIO = max(10, int(PICO*0.5))  # El 50% del pico, con un mínimo de 10

    class PerfilEscalonado(LoadTestShape):
        """
        Perfil escalonado de usuarios, con tres fases: subida, carga sostenida y bajada.
        Tiempo de la prueba: 30 minutos (1800 segundos)
        Inicio (3 min) - subida (4 min) - carga sostenida (10 min) - bajada (1 min) - fin bajada (12 min)
        """

        # Duración de la etapa, usuarios, usuarios/segundo
        stages = [
            {"duration": 180, "users": BASE, "spawn_rate": 5},  # Inicio
            {"duration": 240, "users": MEDIO, "spawn_rate": 5},  # Subida
            {"duration": 600, "users": PICO, "spawn_rate": 10},  # Carga sostenida
            {"duration": 60, "users": BASE, "spawn_rate": 20},  # Bajada abrupta
            {"duration": 720, "users": BASE, "spawn_rate": 5}, # Cola Bajada 
        ]

        def tick(self):
            run_time = self.get_run_time()

            for stage in self.stages:
                if run_time < stage["duration"]:
                    return (stage["users"], stage["spawn_rate"])
                run_time -= stage["duration"]
            return None
