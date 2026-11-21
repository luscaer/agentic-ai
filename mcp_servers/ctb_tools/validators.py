from datetime import date, time
import re
from .schemas import Notificacao


def validar_notificacao(notificacao: dict | Notificacao) -> dict:
    """Relata ausências e inconsistências; não decide validade ou nulidade."""
    entrada = Notificacao.model_validate(notificacao)
    dados = entrada.model_dump()
    ausentes = []
    inconsistencias = []
    alertas = []

    campos_basicos = [
        "numero_auto", "tipificacao", "local", "data_infracao", "hora_infracao",
        "placa", "marca", "especie", "orgao_autuador",
    ]
    if entrada.tipo == "autuacao":
        campo_prazo = "data_limite_defesa"
    else:
        campo_prazo = "data_limite_recurso"
    campos_basicos.append(campo_prazo)

    for campo in campos_basicos:
        if not (dados[campo] or "").strip():
            ausentes.append(campo)
    if not ((entrada.agente_autuador or "").strip() or (entrada.equipamento or "").strip()):
        ausentes.append("agente_autuador_ou_equipamento")
    if not (entrada.prontuario_condutor or "").strip():
        alertas.append("Prontuário do condutor não informado: exigência condicionada à possibilidade (art. 280 IV).")
    if entrada.assinatura_infrator is not True:
        alertas.append("Assinatura ausente ou desconhecida: não é obrigatória em todos os casos (art. 280 VI).")

    datas = {}
    for campo in ["data_infracao", "data_expedicao", campo_prazo]:
        valor = dados[campo]
        if not (valor or "").strip():
            continue
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
                raise ValueError
            datas[campo] = date.fromisoformat(valor)
        except ValueError:
            inconsistencias.append({"campo": campo, "mensagem": "Data inválida; use AAAA-MM-DD."})
    if (entrada.hora_infracao or "").strip():
        try:
            if not re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", entrada.hora_infracao):
                raise ValueError
            time.fromisoformat(entrada.hora_infracao)
        except ValueError:
            inconsistencias.append({"campo": "hora_infracao", "mensagem": "Hora inválida; use HH:MM ou HH:MM:SS."})

    for anterior, posterior in [
        ("data_infracao", "data_expedicao"),
        ("data_infracao", campo_prazo),
        ("data_expedicao", campo_prazo),
    ]:
        if anterior in datas and posterior in datas and datas[posterior] < datas[anterior]:
            inconsistencias.append({"campo": posterior, "mensagem": f"Data anterior a {anterior}."})
    if "data_expedicao" not in datas:
        alertas.append("Data de expedição ausente ou inválida: comparação cronológica limitada.")

    return {
        "tipo": entrada.tipo,
        "campos_ausentes": ausentes,
        "inconsistencias": inconsistencias,
        "alertas": alertas,
        "status": "pendencias_para_conferencia" if ausentes or inconsistencias else "sem_pendencias_nas_verificacoes_realizadas",
        "base_legal": "CTB, arts. 280, 281-A e 282 § 4º; Res. CONTRAN 918/2022, arts. 4º e 12",
        "observacao": (
            "Conferência básica dos dados transcritos de notificação individual. "
            "Não conclui pela validade ou nulidade. Ausência na entrada não comprova ausência no documento. "
            "Não verifica todos os requisitos da notificação, autenticidade, prazos legais, "
            "descontos, editais ou requisitos específicos da infração."
        ),
    }
