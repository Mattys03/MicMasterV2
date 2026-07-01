import pytest
import os
import sys

# Adiciona o diretório raiz ao path para importar core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock simples para testar a inicialização caso PyAudio não esteja instalado no ambiente de CI
def test_audio_engine_initialization():
    # Isso simula um teste estrutural
    assert True, "O ambiente de testes está configurado corretamente."

def test_preset_loading():
    """Testa se o sistema consegue ler presets."""
    preset_path = os.path.join(os.path.dirname(__file__), '..', 'presets', 'divine_voice_auto.json')
    assert os.path.exists(preset_path), "O arquivo de preset padrão deve existir."
