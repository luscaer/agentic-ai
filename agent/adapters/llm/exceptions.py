class LLMInitError(RuntimeError):
    """
    Levantada quando o cliente LLM não pode ser inicializado.
    
    Camada de API → 503 Service Unavailable
    """

    def __init__(self, model_id: str, motivo: str) -> None:
        self.model_id = model_id
        self.motivo = motivo
        super().__init__(f"Falha ao inicializar modelo '{model_id}': {motivo}")