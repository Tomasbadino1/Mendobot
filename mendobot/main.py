"""Punto de entrada de MendoBot (RF-08)."""

from pathlib import Path

from src.data_manager import DataManager
from src.engine import MendoBotEngine


def main() -> None:
    """Inicia el servicio local en modo consola."""
    base_dir = Path(__file__).parent
    candidate_paths = [
        base_dir / "data" / "knowledge_base.json",
        base_dir / "data" / "data" / "knowledge_base.json",
        base_dir / "src" / "knowledge_base.json",
    ]
    data_path = next((path for path in candidate_paths if path.exists()), candidate_paths[0])
    data_manager = DataManager(data_path)
    data_manager.load()
    engine = MendoBotEngine(data_manager)

    print("MendoBot iniciado (servicio local). Escribí 'salir' para terminar.")
    while True:
        user_query = input("Consulta: ").strip()
        if user_query.lower() in {"salir", "exit", "quit"}:
            print("MendoBot finalizado.")
            break

        response = engine.answer(user_query)
        print(f"Bot: {response['message']}")
        if response["animate_avatar"]:
            print("Avatar: animación activada.")


if __name__ == "__main__":
    main()
