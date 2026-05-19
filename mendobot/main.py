"""Punto de entrada de MendoBot (RF-08)."""

from pathlib import Path

from src.data_manager import DataManager
from src.engine import MendoBotEngine

# CU-01 E1: mensaje cuando la consulta no está en la base de conocimiento.
MENSAJE_NO_ENCONTRADO = "No encontré la informacion pedida. ¿Podés reformular la consulta?"


def main() -> None:
    # implements: RF-08
    base_dir = Path(__file__).parent
    data_path = base_dir / "data" / "knowledge_base.json"
    data_manager = DataManager(data_path)
    engine = MendoBotEngine(data_manager)

    print("MendoBot iniciado (servicio local). Escribí 'salir' para terminar.")
    while True:
        consulta = input("Consulta: ").strip()
        if consulta.lower() in {"salir", "exit", "quit"}:
            print("MendoBot finalizado.")
            break

        if not consulta:
            continue

        respuesta = engine.buscar_respuesta(consulta)
        mensaje = respuesta["message"] if respuesta["found"] else MENSAJE_NO_ENCONTRADO
        print(f"Bot: {mensaje}")
        if respuesta.get("animate_avatar"):
            print("Avatar: animación activada.")


if __name__ == "__main__":
    main()
