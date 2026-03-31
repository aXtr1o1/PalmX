from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

connections.connect("default", host="65.1.13.136", port="19530")

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
]
schema = CollectionSchema(fields, description="test bucket connection")
collection = Collection("test_bucket_collection", schema=schema)
print("Collection created successfully!")
