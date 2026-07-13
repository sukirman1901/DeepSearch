from db.embeddings import EmbeddingModel

def test_embedding_model_initializes():
    model = EmbeddingModel()
    assert model is not None

def test_embedding_model_embed_text():
    model = EmbeddingModel()
    embedding = model.embed("test text")
    assert isinstance(embedding, list)
    assert len(embedding) == 384

def test_embedding_model_embed_batch():
    model = EmbeddingModel()
    embeddings = model.embed_batch(["text one", "text two"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
