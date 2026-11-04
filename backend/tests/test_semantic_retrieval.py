from app.services.semantic_retrieval import embedding, cosine, hybrid_similarity

def test_embedding_is_normalized_and_repeatable():
    a=embedding('GlowSerum hydration lasts four weeks')
    assert len(a)==96 and abs(cosine(a,a)-1)<1e-6
    assert a==embedding('GlowSerum hydration lasts four weeks')

def test_hybrid_retrieval_prefers_related_text():
    related=hybrid_similarity('GlowSerum hydration lasts four weeks','GlowSerum hydration duration 4 weeks')
    unrelated=hybrid_similarity('GlowSerum hydration lasts four weeks','The shipping box is brown')
    assert related>unrelated
