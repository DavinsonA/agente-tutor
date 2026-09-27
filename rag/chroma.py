import os

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
CHROMA_URL = os.getenv("CHROMA_URL", "http://localhost:8000")
COLECCION = os.getenv("COLECCION", "tutorias")

BASE = f"{CHROMA_URL}/api/v2/tenants/default_tenant/databases/default_database/collections"


def embeber(textos):
    r = requests.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBEDDING_MODEL, "input": textos}, timeout=300)
    r.raise_for_status()
    return r.json()["embeddings"]


def coleccion(nombre=COLECCION):
    r = requests.post(BASE, json={"name": nombre, "metadata": {"hnsw:space": "cosine"}, "get_or_create": True})
    r.raise_for_status()
    return r.json()["id"]


def borrar(nombre=COLECCION):
    requests.delete(f"{BASE}/{nombre}")


def upsert(id_coleccion, ids, embeddings, documentos, metadatos):
    r = requests.post(
        f"{BASE}/{id_coleccion}/upsert",
        json={"ids": ids, "embeddings": embeddings, "documents": documentos, "metadatas": metadatos},
    )
    r.raise_for_status()


def contar(id_coleccion):
    return requests.get(f"{BASE}/{id_coleccion}/count").json()


def buscar(id_coleccion, embedding, k=5, filtro=None):
    cuerpo = {"query_embeddings": [embedding], "n_results": k, "include": ["documents", "metadatas", "distances"]}
    if filtro:
        cuerpo["where"] = filtro
    r = requests.post(f"{BASE}/{id_coleccion}/query", json=cuerpo)
    r.raise_for_status()
    return r.json()
