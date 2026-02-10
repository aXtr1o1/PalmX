from app.backend.services.rag_service import rag_service

if __name__ == "__main__":
    print("Starting Index Build...")
    rag_service.build_index()
    print("Done.")
