from qdrant_client import QdrantClient

# Cấu hình QDRANT
QDRANT_CLOUD_URL = "https://9657f5df-322f-491b-b41d-297ae18c1859.us-east-1-0.aws.cloud.qdrant.io:6333"  # sửa URL của bạn
QDRANT_API_KEY = "yJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.az-I5w_lXapsV3DijKXoU4Kq-1jxDG13sBBgpbAKoKg"  # thay API KEY của bạn

client = QdrantClient(
    url=QDRANT_CLOUD_URL,
    # api_key=QDRANT_API_KEY
)

def ensure_index_all_collections(client):
    INDEX_FIELDS = [
        {"field_name": "accessType", "field_schema": "keyword"},
        {"field_name": "active", "field_schema": "bool"}
    ]

    try:
        collections = client.get_collections().collections
        print(f"\n==> Có {len(collections)} collection sẽ kiểm tra index")

        for collection in collections:
            collection_name = collection.name
            print(f"\n==> Đánh index cho collection: {collection_name}")

            # Lấy schema hiện có
            desc = client.get_collection(collection_name)
            existing_fields = desc.payload_schema.keys() if desc.payload_schema else []

            for field in INDEX_FIELDS:
                if field["field_name"] in existing_fields:
                    print(f"    [OK] Đã có index cho '{field['field_name']}', bỏ qua")
                    continue
                try:
                    client.create_payload_index(
                        collection_name=collection_name,
                        field_name=field["field_name"],
                        field_schema=field["field_schema"]
                    )
                    print(f"    [+] Tạo index '{field['field_name']}' OK")
                except Exception as e:
                    print(f"    [ERR] Lỗi khi tạo index '{field['field_name']}': {e}")

    except Exception as e:
        print(f"[FATAL] Lỗi khi lấy danh sách collection: {e}")

if __name__ == "__main__":
    ensure_index_all_collections(client)
