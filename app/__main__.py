from app.sample import ensure_sample

import uvicorn


def main() -> None:
    ensure_sample()
    uvicorn.run("app.server:app", host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
