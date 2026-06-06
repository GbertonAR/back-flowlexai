import asyncio
import uuid
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.modules.assistant.orchestrator import run_assistant
from app.db.session import engine
from sqlmodel import Session, select
from app.models.auditoria import AuditoriaLog

async def test_compliance():
    print("🌐 [TEST] Iniciando verificación de cumplimiento WFD...")
    
    tenant_id = 1
    # Consulta de bajo impacto
    query_low = "¿Qué es una ley?"
    print(f"🧠 [TEST] Probando consulta LOW: {query_low}")
    result_low = await run_assistant(tenant_id, query_low)
    print(f"✅ [OK] Impacto: {result_low['impact_level']} | Bloqueado: {result_low['requires_hitl']}")
    
    # Consulta de alto impacto
    query_high = "Procedimiento para derogar la Constitución Nacional"
    print(f"🧠 [TEST] Probando consulta HIGH (Bloqueo esperado): {query_high}")
    result_high = await run_assistant(tenant_id, query_high)
    print(f"✅ [OK] Impacto: {result_high['impact_level']} | Bloqueado: {result_high['requires_hitl']}")
    
    if result_high['requires_hitl']:
        print("🛡️ [GUARD] Bloqueo HITL exitoso.")
        if "⚠️ [REVISIÓN REQUERIDA]" in result_high['response']:
            print("✅ [OK] Mensaje de retención detectado.")
    
    # Verificar Hashing en DB
    print("🔍 [TEST] Verificando integridad del rastro en DB...")
    with Session(engine) as session:
        statement = select(AuditoriaLog).where(AuditoriaLog.request_id == result_high['request_id'])
        log = session.exec(statement).first()
        if log and log.content_hash:
            print(f"✅ [OK] Hash de integridad generado: {log.content_hash}")
        else:
            print("❌ [FAULT] El log no tiene hash de integridad.")

if __name__ == "__main__":
    asyncio.run(test_compliance())
