# MicMaster Pro

<div align="center">
  <a href="https://github.com/Mattys03/MicMasterV2/releases/latest">
    <img src="https://img.shields.io/badge/📦_Download_Release-0078D4?style=for-the-badge&logo=github" alt="Download Release" />
  </a>
</div>

![Platform](https://img.shields.io/badge/Plataforma-Windows-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![License](https://img.shields.io/badge/Licen%C3%A7a-MIT-purple)
[![Python application](https://github.com/Mattys03/MicMasterV2/actions/workflows/python-app.yml/badge.svg)](https://github.com/Mattys03/MicMasterV2/actions/workflows/python-app.yml)

**MicMaster Pro** é um painel de controle *Desktop* completo para diagnóstico e gerenciamento de sistemas de áudio. Construído em Python com interface Tkinter, a aplicação visa oferecer um ambiente profissional para monitorar captação de microfone, visualizar níveis de sinal e salvar perfis (presets) personalizados.

## 🚀 Funcionalidades

- **Monitoramento de Sinal (VU Meter):** Visualização instantânea da amplitude e força do sinal do microfone em tempo real.
- **Gerenciador de Presets:** Sistema completo para salvar, carregar e alternar entre diferentes configurações de equalização e ganho no formato JSON.
- **Diagnóstico de Hardware:** Painel dedicado para varredura do sistema operacional, exibindo detalhes técnicos dos dispositivos de áudio de entrada e saída.

## 🛠️ Arquitetura e Tecnologias

- **Linguagem:** Python 3.10+
- **Interface Gráfica:** `Tkinter` e `ttkbootstrap` (para um design mais moderno).
- **Processamento de Áudio:** `PyAudio` / `sounddevice` para buffer e leitura de streams em tempo real.

## 📦 Como Usar

1. Baixe o projeto pelo link de Release acima.
2. Instale as dependências executando `pip install -r requirements.txt`.
3. Inicie o sistema através do arquivo principal na pasta raiz ou interface dedicada.
4. Navegue pela aba de **Diagnóstico** para escanear os periféricos de áudio ativos.

## 📝 Licença

Distribuído sob a Licença MIT.
