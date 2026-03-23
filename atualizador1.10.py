import os
import sys
import json
import logging
import requests
import subprocess
import tempfile
import time
import winreg
import psutil
import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QProgressBar, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QByteArray, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap

# --- LOGGING ---
def configurar_logging():
    if getattr(sys, 'frozen', False):
        pasta_log = os.path.dirname(sys.executable)
    else:
        pasta_log = os.path.dirname(os.path.abspath(__file__))
    arquivo_log = os.path.join(pasta_log, "atualizador.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(arquivo_log, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    # Limitar tamanho do log (manter últimas 500KB)
    try:
        if os.path.exists(arquivo_log) and os.path.getsize(arquivo_log) > 500 * 1024:
            with open(arquivo_log, 'r', encoding='utf-8', errors='ignore') as f:
                linhas = f.readlines()
            with open(arquivo_log, 'w', encoding='utf-8') as f:
                f.writelines(linhas[-2000:])
    except Exception:
        pass
    return logging.getLogger('atualizador')

log = configurar_logging()

# --- CONFIGURAÇÕES ---
TIMEOUT_INSTALACAO = 600  # 10 minutos máximo para instalação
TIMEOUT_DOWNLOAD = 300    # 5 minutos máximo para download
URL_API = "https://download-api.inovafarma.com.br/graphql"
NOME_SISTEMA_BUSCA = "InovaFarma"
LOGO_BASE64 = "AAABAAEASEgAAAEAIACIVAAAFgAAACgAAABIAAAAkAAAAAEAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD///8A////AP///wD///8A////AP///wCigVBknng/waN8QvWjfEP/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+jfET/o3xE/6N8RP+kfUP4oHpAxqGATmrX//8B////AP///wD///8A////AP///wD///8A////AP///wD///8AoHxGT591Nr6fdDHynnEv/p5xLv+eci7/n3Iv/59yL/+eci//nnIv/55yL/+eci//n3Iv/59yL/+fci//n3Iv/59yL/+fci//n3Iv/59yL/+fci//n3Iv/59yL/+fci//n3Iv/59yL/+fci//n3Iv/55yL/+eci//n3Iv/55yL/+fci//n3Iv/59yL/+fci//n3Iv/59yL/+fci//n3Iv/59yL/+fci//n3Iv/59yL/+fci//n3Iv/59yL/+fci//n3Iv/59yL/+fci//n3Iv/59zL/+fcy//n3Mv/59zL/+fcy//n3Mv/55yLv+ecS7/nnEv/p9zMfOfdjfDoXxGV////wD///8A////AP///wD///8A////AP///wCfdzyYn3Mw/59xLf+ecC3/oHUx/6R8M/+pgTH/rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgy//rIMv/6yDL/+sgi//rIIv/6yCL/+sgi//rIIv/6qBMf+mfjP/oXcy/55xLf+fcSz/n3Mv/6B4PaSFxP8B////AP///wD///8A////AJ54PJmfci7/n3Et/55yMP+lfTP/t4km/8iQFP/Qkwn/1JQF/9WUBf/VlAX/1ZQF/9SUBf/UlAb/1JQG/9SVBv/UlQb/1ZUG/9WVBv/UlQb/1ZUG/9WVBv/UlQb/1ZUG/9WVBv/UlQb/1ZUG/9WVBv/UlQb/1JUG/9SUBv/UlAX/1JQF/9WUBf/VlAX/1JQF/9SUBf/TkwX/0pMF/9KSBf/SkgX/0pIF/9KSBf/SkgX/0pIF/9KSBf/SkgX/0ZEF/9CQBf/QjwX/zo4F/82MBf/MiwX/yooF/8qJBf/JiAX/yIcF/8eFBf/GhAX/xIMF/8GCCf+9gxP/s4Ql/6Z/Mv+eczD/n3Et/59yLv+geD2p////AP///wD///8An3tFS59zMP+fcS3/nXEw/6qBL//KkRL/2pYA/9yWAP/blgD/2pYA/9qWAP/algD/2pYA/9uXAP/blwD/25cA/9uXAP/blwD/25cA/9uXAP/blwD/25cA/9uXAP/blwD/25cA/9uXAP/blwD/25cA/9uXAP/blwD/25cA/9uXAP/blwD/2pcA/9qWAP/algD/2pYA/9qWAP/algD/2pUA/9mVAP/YlAD/15MA/9eTAP/XkwD/15MA/9eTAP/XlAD/15MA/9aTAP/VkgD/1ZAA/9OPAP/SjQD/0YwA/8+LAP/OiQD/zYgA/8yHAP/KhQD/yYQA/8iCAP/HgAD/xn8A/72CEP+rgS7/nnMw/59xLf+eczD/oHxFWf///wC/yeEEn3U2xJ9yLf+dcC//qH0u/9KUCv/dlgD/2ZUA/9iVAP/YlgH/2ZYB/9qWAf/algH/2pYB/9qWAf/ZlgH/2ZcA/9mXAP/ZlwD/2ZcA/9mXAP/ZlwD/2ZcA/9mXAP/ZlwD/2ZcA/9mXAP/ZlwD/2ZcA/9mXAP/ZlwD/2JcA/9mXAP/ZlgH/2pYB/9qWAf/algH/2ZYB/9mWAf/YlgH/2ZUA/9mVAP/ZlQD/2JUA/9eUAP/WkwD/1pMA/9aTAP/WkwD/1pMA/9aTAP/WkwD/1ZIA/9SRAP/TjwD/0o4A/9GMAP/OiwD/zYoA/8yJAP/LhwD/yoYA/8iEAP/HggD/xYEA/8d/AP/BgAj/qX4t/51xMP+fciz/n3U2z6WYhwugfkxjn3Mx955xLf+fdDH/ypAQ/92XAP/YlgH/2ZYB/9qWAf/algH/2pYB/9mXAP/ZlwD/2ZcA/9mXAP/ZlwD/2pcA/9qXAP/alwD/25cA/9uXAP/bmAD/25gA/9uYAP/bmAD/25gA/9uYAP/blwD/25cA/9qXAP/alwD/2pcA/9mXAP/ZlwD/2ZcA/9mXAP/ZlwD/2ZYB/9qWAf/algH/2ZYB/9mWAf/ZlQD/2ZUA/9mVAP/YlQD/15QA/9aTAP/WkwD/1pMA/9aTAP/WkwD/1pMA/9WSAP/UkQD/1JAA/9KOAP/RjQD/z4sA/82KAP/NiQD/zIcA/8qGAP/IhAD/x4IA/8WBAP/GfwD/vYEO/6F3Mf+ecS7/n3Mw+qB9SXueeD7Gn3Iu/5twMP+xgST/3JgA/9mWAf/algH/2pYB/9mWAf/ZlwD/2ZcA/9mXAP/alwD/2pcA/9uYAP/bmAD/25gA/9uYAP/bmAD/25gA/9uYAP/bmAD/25gA/9uYAP/bmAD/25gA/9uYAP/bmAD/25gA/9uYAP/bmAD/25gA/9uYAP/bmAD/2pcA/9qXAP/ZlwD/2ZcA/9mXAP/ZlwD/2pYB/9qWAf/algH/2ZYB/9iWAf/ZlQD/2ZUA/9iVAP/WlAD/1pMA/9aTAP/WkwD/1pMA/9aTAP/WkwD/1JIA/9SQAP/SjwD/0Y0A/8+LAP/NigD/zYkA/8yIAP/KhgD/yYQA/8eCAP/FgQD/x4AA/658Iv+ccTH/n3Iu/6F7QOijfEL8n3Iu/5twMf/GjBL/3pgA/9qWAf/ZlgH/2ZcA/9mXAP/alwD/2pcA/9uYAP/bmAD/25gA/9uYAP/bmAD/25gA/9uYAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/bmAD/25gA/9uYAP/bmAD/25gA/9uYAP/bmAD/25cA/9qXAP/ZlwD/2ZcA/9mXAP/ZlgH/2pYB/9mWAf/YlgH/2JYB/9mVAP/ZlQD/15QA/9aTAP/WkwD/1pMA/9aTAP/WkwD/1pMA/9WSAP/UkAD/048A/9GNAP/QjAD/zYoA/82JAP/MiAD/yoYA/8iEAP/HggD/x4EA/7t+D/+dcjH/n3Iu/59zMf+ie0H/nnIu/59yL//RkQj/25gA/9mXAP/ZlwD/2pcA/9uYAP/bmAD/25gA/9uYAP/bmAD/25gA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9uYAP/bmAD/25gA/9uYAP/bmAD/2pcA/9qXAP/ZlwD/2ZcA/9mWAf/algH/2ZYB/9iWAf/ZlQD/2ZUA/9iVAP/WlAD/1pMA/9aTAP/WkwD/1pMA/9aTAP/VkgD/1JEA/9OPAP/RjQD/0IwA/82KAP/NiQD/zIgA/8qGAP/IhAD/yIMA/8GABv+gcy3/nnIv/59yLf+ie0H/nnIv/6F0LP/TkwX/25gA/9qXAP/bmAD/25gA/9uYAP/bmAD/25gA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9uYAP/bmAD/25gA/9uYAP/blwD/2pcA/9mXAP/ZlwD/2pYB/9qWAf/ZlgH/2JYB/9mVAP/ZlQD/15QA/9aTAP/WkwD/1pMA/9aTAP/WkwD/1ZIA/9SRAP/TjwD/0Y4A/9CMAP/NigD/zYkA/8yHAP/KhgD/yYQA/8SBA/+icyv/nnIv/59yLv+ie0H/nnIv/6F0LP/UlAX/3ZkA/9uYAP/bmAD/25gA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JoA/9yaAP/cmgD/3JoA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/25gA/9uYAP/bmAD/25gA/9qXAP/alwD/2JcA/9mXAP/algH/2ZYB/9iWAf/ZlQD/2ZUA/9eVAP/WkwD/1pMA/9aTAP/WkwD/1pMA/9WSAP/UkQD/048A/9GNAP/QjAD/zYoA/82JAP/LhwD/yoUA/8WDA/+icyv/nnIv/59yLv+ie0H/nnIv/6F0LP/VlAX/3ZkA/9uYAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmgD/3ZoA/92aAP/dmwD/3ZsA/92bAP/dmwD/3ZsA/92bAP/dmwD/3ZsA/92bAP/dmwD/3ZsA/92bAP/dmwD/3ZoA/92aAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmQD/25gA/9uYAP/bmAD/2pcA/9mXAP/YlwD/2pYB/9qWAf/ZlgH/2JUA/9mVAP/YlQD/1pMA/9aTAP/WkwD/1pMA/9aTAP/VkgD/1JEA/9OPAP/RjQD/z4sA/82KAP/NiQD/zIgA/8eEA/+icyv/nnIv/59yLv+ie0H/nnIv/6F0LP/VlAX/3poA/9yZAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9yZAP/cmAD/25QA/9uVAP/dmQD/3ZsA/92bAP/dmwD/3ZsA/92bAP/dmwD/3ZsA/92bAP/dmwD/3ZsA/92bAP/dmwD/3ZsA/92bAP/dmwD/3ZsA/92bAP/dmwD/3ZsA/92aAP/blAD/2pIA/9uUAP/cmQD/3JkA/9yZAP/cmQD/3JkA/9uYAP/bmAD/25gA/9uYAP/alwD/2JYA/9mVAP/alQD/2ZYB/9iWAf/ZlQD/2JUA/9aTAP/WkwD/1pMA/9aTAP/WkwD/1ZIA/9SRAP/TjwD/0Y0A/8+LAP/NigD/zYkA/8iFA/+idCv/nnIv/59yLv+ie0H/nnIv/6F0LP/WlQX/3poA/9yZAP/cmQD/3JkA/9yZAP/cmgD/3ZoA/9uUAP/doA//47VE/+O1Rv/doRH/25QA/96cAP/enAH/3pwB/96cAf/enAH/3pwB/96cAf/enAH/3pwB/96cAf/enAH/3pwB/96cAf/enAH/3pwB/96cAf/dnAD/3JYA/9qWAP/irzT/5r1a/+GtMf/ZkwD/3JcA/9yZAP/cmQD/3JkA/9yZAP/cmQD/25kA/9qVAP/YkAD/2ZcC/9iaCP/WkQD/2I8A/9mWAP/YlgH/2ZUA/9iVAP/WlAD/1pMA/9aTAP/WkwD/1pMA/9WSAP/UkQD/0o8A/9GNAP/OiwD/zooA/8mHA/+idCv/nnEv/59yLv+ie0H/nnIv/6F0LP/WlQX/3poA/9yZAP/cmQD/3JkA/92aAP/dmwD/2pQA/+a/Yf/69eb////////////79ur/6MJo/9uVAP/enAH/3p0B/96dAP/enQD/3p0A/96dAP/enQD/3p0A/96dAP/enQD/3p0B/96cAf/enAH/3pwB/96cAf/clQD/36cm//Lgsv/+//////////7////t05P/2pUA/9yYAP/cmQD/3JkA/9yZAP/cmgD/2pMA/9yfGP/t05T/+PDb//nz5f/y4rr/4LNK/9eOAP/ZlQD/2JYB/9mVAP/YlQD/1pMA/9aTAP/WkwD/1pMA/9aTAP/VkgD/1JAA/9KOAP/RjAD/z4sA/8qIA/+idCv/nnEv/59yLv+ie0H/nnIv/6F0LP/WlQX/3poA/9yZAP/dmgD/3ZsA/92bAP/blAD/5r5c/////////////v7///7+/////////////+jDZv/clgD/354A/9+eAP/fngD/354A/9+eAP/fngD/354A/9+eAP/fngD/354A/9+eAP/fngD/354A/9yVAP/isDr//Prw///////+/////v7+////////////7NCJ/9qTAP/dmgD/3JkA/9yZAP/blAD/3qQk//nz4f///////////////////////////+fEdP/XjgD/2pYB/9iWAf/ZlQD/2JUA/9aTAP/WkwD/1pMA/9aTAP/WkwD/1JEA/9SQAP/SjgD/0YwA/8qJA/+idCv/nnEv/59yLv+ie0H/nnEv/6F0LP/WlQX/35sA/92bAP/dmwD/3ZsA/92ZAP/eohT/+/nx///////+/v7//v7+//7+/v/+/v7///////z79v/gphr/35sA/9+eAP/fngD/350A/+CdAP/gnQD/4J0A/+CdAP/gnQD/354A/9+eAP/fnwD/3ZcA/+GsLv/7+e7///////7+/v/+/v7//v7+//7+/v/+/////v///+GtMf/clgD/3ZsA/9yYAP/algT/9uvO///////+/v7//v7+//7+/v/+/v7////////////fsD//2JAA/9mWAf/YlgH/2ZUA/9iVAP/WkwD/1pMA/9aTAP/WkwD/1pMA/9SRAP/TjwD/0o4A/8yKA/+idCv/nnEv/59yLv+jfEL/n3Iw/6J1Lf/XlwX/35wA/92bAP/enAH/3pwB/9uUAP/pxm3///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////synj/3ZUA/+CdAP/gnQD/4J0A/+CdAP/gnQD/4J0A/+CdAP/gnQD/4J0A/+CdAP/elgD/4agm//r26P///////v7+//7+/v/+/v7//v7+//7+/v/+/v7///////Daov/akwD/3ZsA/9uUAP/lu1P///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////y5L3/1ZEA/9qWAP/ZlgH/2JYB/9mVAP/XlQD/1pMA/9aTAP/WkwD/1pMA/9WSAP/UkQD/048A/86LA/+jdSz/n3Iw/59zL/+tg07/qno9/6x8Ov/YmAb/35wA/96cAf/enAH/3pwB/9yWAP/y4LD///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////05Ln/3pkA/+CeAP/gnwD/4Z8A/+GfAP/hnwD/4J8A/+CfAP/gnwD/4J8A/9+YAP/hph3/+fPg///////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7///////n05f/dngn/3ZoA/9qUAP/w26b///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////8/Pn/26Ea/9eUAP/algH/2ZYB/9mVAP/ZlQD/15QA/9aTAP/WkwD/1pMA/9aTAP/VkgD/1ZAA/8+NBP+tfDj/qns9/6l7PP+2iVj/tIJH/7eDRP/ZmQj/350A/96cAf/enQH/354A/92aAP/26cj///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////37dL/350A/+GeAP/hnwD/4Z8A/+GfAP/hnwD/4Z8A/+GfAP/hoAD/4JoA/+CkFv/48Nj///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7///////39/P/gqCH/3ZgA/9uYAP/16cn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7/////////4K06/9eRAP/YlwD/2pYB/9iWAf/ZlQD/2ZUA/9aUAP/WkwD/1pMA/9aTAP/WkwD/1ZIA/9KOBP+3g0H/tIJI/7SCR/+6jVz/uoZM/7yHSP/amgj/350A/96dAP/fngD/354A/92aAP/26cr///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////37tP/354A/+GfAP/hoAH/4qAB/+KgAf/ioAH/4qAB/+KgAf/gnAD/4KEP//ftz////////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/iqyf/3ZgA/9yZAP/26s7///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+////////4rFC/9mRAP/ZlwD/2ZcA/9qWAf/YlgH/2ZUA/9iVAP/WkwD/1pMA/9aTAP/WkwD/1pIA/9KPBf+8h0X/uYZN/7qGS//AkGH/wIlS/8GKTf/bmgn/4J4A/9+eAP/fngD/350A/96ZAP/26cn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////37tP/4J4A/+KfAP/ioAH/4qEA/+KhAP/ioQD/4qEA/+GdAP/goAn/9unE///////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/f/iqyb/3poA/9yaAP/26s3///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+////////4q89/9mQAP/algD/2JcA/9mWAf/algH/2JYB/9mVAP/XlAD/1pMA/9aTAP/WkwD/1pMA/9ORBf/Cikr/wYpS/8CJUP/DkWv/w4pd/8SLWP/cnAn/4J8A/9+eAP/gnQD/4JwA/96aAP/26sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////37tL/4J8A/+KgAP/ioQD/4qEA/+KhAP/ioQD/4Z4A/+CeA//15bn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/f/iqyb/3poA/92bAP/2683///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+////////4rZM/9mYD//ZlgD/2JEA/9iXAP/algH/2ZYB/9mVAP/YlQD/1pQA/9aTAP/WkwD/1pMA/9SSBf/HjU7/xo1X/8aNVf/Yokb/3aEr/+GjIP/fngP/354A/+CdAP/gnQD/4J4A/9+cAP/26sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////37tL/4J8A/+KgAP/ioQD/46IA/+OiAP/inwD/4JwA//Phrv///////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/f/jqyb/35kA/92bAP/2683///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/+/nx//r37f/37NL/47ZQ/9eQAP/ZlwD/2pYB/9iWAf/ZlQD/2JUA/9aTAP/WkwD/1pMA/9WTBv/MkVL/zJFb/8uRWv/tsxX/87IA//KwAP/hnwD/4JwA/+CdAP/gnwD/4Z8A/9+cAP/26sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////37tL/4aAA/+OhAP/jogD/46IA/+OgAP/gnAD/8t2j///////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/jrCb/35kA/96aAP/2683///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//////////////////v///+CtO//XkQD/2pYB/9qWAf/YlgH/2ZUA/9eUAP/WkwD/1pMA/9WTBv/NlFT/zZRc/82UW//qsRz/8K8B/++uAP/hngD/350A/+GfAP/hnwD/4Z8A/9+dAP/36sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////37tL/4aAA/+SiAP/kowD/5KEA/+GcAP/x2Zb///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/krSb/35oA/96aAP/2683///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7///////LhuP/XkAD/2ZcA/9qWAf/ZlgH/2ZUA/9iVAP/WkwD/1pMA/9WTBv/Ol1T/zpdd/86WW//qsRv/8K8B/++uAP/hnwD/4J8A/+GfAP/hoAH/4qAA/+CdAP/36sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////47tL/4qEA/+SiAP/kogD/4psA//DUiv///////v7///7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/krSb/4JsA/96cAP/2683///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7///////r36//bnAz/2JUA/9mWAf/algH/2JYB/9mVAP/XlAD/1pMA/9WUBf/QmVb/0Jlf/8+ZXf/qsRv/8K8B/++uAP/ioAD/4Z8A/+GgAf/ioAH/4qAA/+CeAP/36sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////47tL/46EA/+WiAP/hmgD/7s99///////+/v///v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/krif/4JsA/9+cAP/268z///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7///////v58//coBX/2ZQA/9iXAP/algH/2ZYB/9mVAP/YlQD/1pMA/9WUBf/Sm1f/0pxg/9GcXv/qsRz/8K8B//CuAP/ioAD/4Z8B/+KgAf/ioAH/4qEA/+CeAP/36sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////47tL/4qEA/+GZAP/ty3H///////7////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/lrSf/4JwA/9+dAP/268z///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7///////jw3P/alwT/25YA/9mXAP/ZlwD/2pYB/9iWAf/ZlQD/15QA/9WTBv/Snlf/0p9g/9GfX//qshz/8K8B/++uAP/ioQH/4aAB/+KgAf/ioQD/4qEA/+GeAP/36sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////479L/4ZwA/+zGY////////v////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////3+/f/lrib/4ZwA/9+dAP/268z///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//////+vNg//YkAD/25gA/9qXAP/ZlwD/2pYB/9mWAf/ZlQD/2JQA/9WUBv/ToFj/06Fh/9KhYP/qshz/8K8B/++uAP/joQH/4qAB/+KhAP/ioQD/46EA/+GfAP/36sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////36cT/6Lk//////////////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////3+/f/lrib/4Z0A/+CdAP/268z///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/////////////////9ObD/9uaC//blwD/25gA/9uXAP/ZlwD/2pYB/9mWAf/ZlQD/2ZUA/9WUBv/Vo1r/1aRj/9SkYf/qshz/8K8B/++uAP/joQH/4qEA/+KhAP/ioQD/46IA/+GfAP/36sn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////2577/7slp///////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7///////7////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/f/lrib/4Z0A/+CeAP/3683///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+////8dum/+zNh//nwGP/25kF/9uWAP/cmQD/25gA/9uYAP/ZlwD/2ZcA/9qWAf/YlgH/2ZUA/9aVBv/VpVr/1adj/9SnYf/qshz/8K8B//CuAP/jogD/4qEA/+KhAP/jogD/46IA/+KgAP/368n///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////26L//7sdj///////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v//////+/fq//z47f/+/v///v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/mrib/4Z0A/+CeAP/268z///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+////////4awu/9iLAP/akQD/3JYA/9yYAP/clwD/25cA/9uYAP/alwD/2JcA/9qWAf/ZlgH/2ZUA/9eWBv/XqFv/1qtk/9aqYv/rsh3/8K8B//CuAP/jogD/4qEA/+OiAP/jogD/5KIA/+KgAP/368n///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////26L//7cdi///////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+///////79+j/6LUy//rx2f///////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/mryb/4p0A/+CeAP/268z///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+////////47ZG/9qXBv/cnQf/25sI/9ubCP/bmwj/2pYA/9iQAP/blwD/2ZcA/9mWAf/ZlgH/2ZUA/9iWBv/Xqlz/161l/9esY//rsh3/8K8B//CuAP/jogD/4qEA/+OiAP/kowD/5KMA/+OgAP/368n///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////26L//7cdi///////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7///////z68v/ptDD/5qIA//v15v///////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/mryb/4p4A/+GfAP/268z///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/+fbp//fy4f/48+L/+PPi//jz4v/48+P/9urL/+fCbf/YlAD/2ZQA/9mXAP/algH/2JUA/9iWBv/YrV3/2LBm/9ivZf/rsh3/8K8B/++uAP/kogD/46IA/+OiAP/kowD/5aMA/+KgAP/368n///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////36L//7chi///////+/v7//v7+//7+/v/+/v7//v7+//7+/v///////f34/+q7Pv/mngD/6KoJ//v15f///////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/nsCb/4p4A/+GfAP/368z///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7////////////////////////////////////////////w3Kv/2JMB/9mWAP/algH/2ZUA/9iWBv/ZsF7/2bNn/9myZv/qsh3/8K8B/++uAP/kowD/46IA/+SjAP/kowD/5KMA/+KgAP/368n///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////36L//7shi///////+/v7//v7+//7+/v/+/v7//v7+///////+/v3/7L9J/+egAP/opwD/56oJ//v15f///////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////3+/f/nsCb/454A/+GfAP/37Mz///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+////////6ch6/9aOAP/algH/2ZUA/9iWBv/bsV7/27Vo/9q0Zv/rsh3/8K8B//CuAP/kowD/46IA/+SjAP/lowD/5KIA/+OgAP/368n///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////36L//78li///////+/v7//v7+//7+/v/+/v7///////7////uxFX/6KEA/+qpAP/ppgD/6KsK//v15f///////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////3+/f/nsCb/458A/+GfAP/37Mz///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v//////+/ny/9qdE//ZlAD/2ZUA/9iXBv/ctF7/3Lhp/9u3Z//qsx3/8K8B//CvAP/kowD/46IA/+SjAP/kowD/5KIA/+ShAP/368n///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////36b//78li///////+/v7//v7+//7+/v///////////+/IYP/ooQD/6qkA/+qpAP/qpwD/6asK//v15f///////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////3+/f/nsCb/458A/+KgAP/368z///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//////+S7Wf/WjwD/2pUA/9iXB//ctl//3bpp/925aP/qsx3/8K8B/++vAP/kowD/5KMA/+WjAP/kowD/5aMA/+SiAP/368n///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////36b//78li///////+/v7//v7+//7/////////8M1t/+miAP/rqgD/6qkA/+qpAP/qpwD/6awJ//v25f///////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////3+/f/nsCb/458A/+KgAP/37M3///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//////+vPjP/VjgD/2pUA/9iYB//euWD/3r1q/968af/qsx3/8K8B/++uAP/lpAD/5KMA/+SjAP/kowD/5aQA/+OiAP/368n///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////36b//78pj///////+/v7//v7////////x0nn/6aMA/+urAP/rqwD/66oB/+qpAP/qpwD/6awK//v25v///////v7+//7+/v/+/v7//v7+//7+/v/+/v7//v////7+/v/nsCf/458A/+OiAP/58Nb///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//////+7Wnf/VjgD/2pUA/9iYB//fvGH/4MBr/+C+av/psx3/8K8B//CuAP/lpAD/5KMA/+SjAP/kowD/5aQA/+SiAP/468n///////7+/v///////////////////////v7+///////36b//78pi///////+/v////////LWhf/ppAD/66sA/+urAP/rqwD/66sA/+uqAf/qqAD/6aoF//r04v///////v7+//7+/v/+/v7//v7+//7+/v/+/v7///////39+//mriD/5J8A/+KgAP/37Mz///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//////+zQjv/VjgD/2pUA/9mYB//fvmP/4cNt/+DCa//qsx3/8K8B//CuAP/lpAD/5KMA/+SjAP/lowD/5aUA/+SiAP/468j////////////8+vT/9+zN//fsy//7+vL////////////36b7/78pi////////////9NuS/+qlAP/tqwD/7awA/+ysAP/rrAD/66sA/+urAP/rqgD/6KUA//fqxP///////v7+//7+/v/+/v7//v7+//7+/v/+/v7///////r15f/jpQj/5KIA/+KcAP/z3qb///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//////+W9YP/WjwD/2ZUA/9mYB//hwGT/4sVu/+LEbP/qtB3/8K8B//CuAP/lpAD/5KMA/+SjAP/lpAD/5aUA/+WiAP/57tL//v////DQe//mqAr/5Z4A/+afAP/oqAf/8c92//7+/f/47Mn/78ph///////135//66cA/+2sAP/trgD/7q0A/+2sAP/srAD/66sA/+urAP/rqwD/6aMA//HQdf///////v7+//7+/v/+/v7//v7+//7+/v/+/v7///////Lcnv/inAD/5KMA/+OdAP/qwVT///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v///////Pv3/9ygGf/YlAD/2ZUA/9mYB//hwmT/4sdv/+LGbf/qtB3/8K8B//CuAP/lpAD/5KMA/+SjAP/lpAD/5aUA/+alAv/368n/7L1J/+ObAP/twlD/9N2c//Xenf/vxFT/558A/+29P//257n/8dN8//jnuv/rqAD/7awA/+2uAP/trgD/7a4A/+2uAP/urAD/7KwA/+urAP/rqwD/66gA/+msEP/79ub///////7+/v/+/v7//v7+//7+/v///////f36/+axJv/knwD/5KMA/+WiAP/ioAT/9+3O///////+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v//////68+K/9iPAP/ZlwD/2ZUA/9mYB//jxWX/5Mpw/+TJbv/qtB3/8K8B//CuAP/lpAD/5KMA/+SjAP/lpAD/5aUA/+ioCP/osir/5qMC//bnuv//////////////////////9+rB/+mpBv/qsyH/7b04/+2vC//trAD/7q4A/+2uAP/trgD/7q4A/+2uAP/urQD/7KwA/+urAP/rqwD/66sB/+mkAP/rujr//Prx///////////////////////+////68NZ/+OeAP/lpAD/5KMA/+SjAP/jngD/5Kwl//r15v/////////////////////////////////////////////////////////////////////////////////z5L3/2ZYG/9uWAP/ZlwD/2ZUA/9qYB//kyGX/5c1w/+XMbv/qtB3/8K8B//CuAP/lpAD/5KMA/+SjAP/lpAD/5aUA/+ilAP/lngD/9eW1///////+/v///v7+//7+/v/+/v////////fpvv/ppQD/7KkA/+2sAP/trgD/7q4A/+2uAP/trgD/7a4A/+2uAP/trgD/7awA/+ysAP/rqwD/66sA/+qpAP/powD/6rQn//Teo//69OH/+/Xl//Xjsf/quDv/5Z8A/+WlAP/lpAD/5KMA/+SjAP/kpAD/4pwA/+OpHf/y3KL/+/Xn//z69P/8+vP//Prz//z68//8+fP//Pnz//z68v/8+vL//Pnz//z58//8+fP/+PHd/+vMg//alwX/2pUA/9uYAP/ZlwD/2ZUA/9qYB//kyGb/5c1x/+XMb//qtB3/8K8B//CuAP/lpAD/5KMA/+SjAP/lpAD/5aUA/+egAP/swE3///////7+///+/v7//v7+//7+/v/+/v7//v7+///////vx1f/66YA/+2tAP/trgD/7q4A/+2uAP/trgD/7a4A/+2uAP/trgD/7awA/+usAP/rqwD/66sA/+qpAP/qqQD/6aYA/+eiAP/nqQb/56kJ/+aiAP/noQD/5qUA/+WlAP/lpAD/5KMA/+SjAP/kowD/46IA/+KeAP/gmwD/4qQL/+OnGP/ipxb/4qcW/+GlFv/hpRb/4KUW/+ClFv/fpBf/36QX/96jFv/doRb/25oE/9mRAP/clwD/25gA/9uYAP/ZlwD/2ZUA/9qYB//kyGb/5c1x/+XMb//qtB3/8K8B/++uAP/lpAD/5KMA/+SjAP/lpAD/5aUA/+WgAP/147H///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////26Lv/6qcA/+2sAP/trgD/7a4A/+6uAP/trgD/7q4A/+2uAP/trQD/7KwA/+urAP/rqwD/66oB/+qpAP/qqQD/6qkA/+moAP/opwD/6KYA/+inAP/opgH/5qUA/+WlAP/lowD/5KMA/+SjAP/kowD/46IA/+OiAP/ioQD/4p8A/+KeAP/gnQD/4J0A/9+aAP/fmgD/3pwA/96aAP/dmQD/3ZkA/9yYAP/blwD/3JgA/9yZAP/cmQD/25gA/9uYAP/ZlwD/2ZUA/9mZB//kyGb/5c1x/+XMb//qtR3/8K8B//CvAP/lpAD/5KMA/+SjAP/lpAD/5aQA/+anBv/69OP///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////69+r/6q8L/+yrAP/trAD/7a4A/+2uAP/trgD/7a4A/+6tAP/trAD/7KwA/+urAP/rqwD/66oB/+qpAP/qqQD/6qkA/+moAP/nqAD/6KcA/+inAf/opgH/5qUA/+WlAP/kowD/5KMA/+SjAP/kowD/46IA/+OiAP/ioQD/4qAB/+GgAf/hnwD/4J8A/+CdAP/fngD/354A/96dAP/enAH/3ZsA/92bAP/cmgD/3JkA/9yZAP/cmQD/25gA/9uYAP/ZlwD/2ZUA/9qZB//kyGb/5c1x/+XMb//qtR3/8K8B//CvAP/lpAD/5KMA/+SjAP/lpAD/5aMA/+etGP/8+/T///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7////9/Pn/7LUf/+upAP/srAD/7awA/+2tAP/trQD/7a0A/+2sAP/srAD/66sA/+urAP/rqwD/66kB/+qpAP/qqQD/6agA/+ioAP/nqAD/6KcA/+imAf/opgH/5aUA/+WlAP/kowD/5KMA/+WjAP/kowD/46IA/+KhAP/ioQD/4qAB/+GgAf/hnwD/4J8A/+CdAP/fngD/354A/96dAP/enAH/3ZsA/92bAP/cmgD/3JkA/9yZAP/cmQD/25gA/9uYAP/ZlwD/2ZUA/9qZB//kyGb/5c1x/+XMb//rtR3/8K8B//CuAP/lpAD/5KMA/+SjAP/kowD/5aMA/+asFP/8+vL///////7+/v/+/v7//v7+//7+/v/+/v7//v7+//7////9/Pf/7LQb/+upAP/rqwD/7KwA/+ysAP/srAD/7KwA/+ysAP/rqwD/66sA/+urAP/rqgH/6qkA/+qpAP/qqQD/6agA/+ioAP/opwD/6KcA/+imAf/npgH/5aUA/+WkAP/kowD/5KMA/+SjAP/jogD/46IA/+KhAP/ioQD/4qAB/+GgAf/hnwD/4J4A/+CdAP/fngD/354A/96dAP/enAH/3ZsA/92bAP/cmQD/3JkA/9yZAP/cmQD/25gA/9uXAP/ZlwD/2pUA/9mZB//kyGb/5c1x/+XMb//stR3/8K8B//CuAP/lpAH/5KMA/+SjAP/kowD/5aQA/+SkAv/58dn///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////69OH/6qsG/+uqAP/rqwD/66sA/+urAP/rqwD/66sA/+urAP/rqwD/66sA/+uqAf/qqQD/6qkA/+qpAP/qqAD/6agA/+eoAP/opwD/6KcA/+imAf/npQD/5aUA/+WkAP/kowD/5KMA/+SjAP/jogD/46IA/+KhAP/ioQD/4qAB/+GgAf/hnwD/4J4A/+CdAP/fngD/354A/96cAf/enAH/3ZsA/92bAP/cmQD/3JkA/9yZAP/cmQD/25gA/9qXAP/ZlwD/2pUA/9mZB//kyGb/5c1w/+XMb//stR3/8K8B//CuAP/lpAH/5KMA/+WjAP/kowD/5aQA/+OeAP/y25r///////7+/v/+/v7//v7+//7+/v/+/v7//v7+///////04KX/6KMA/+uqAf/rqwD/66sA/+urAP/rqwD/66sA/+urAP/rqgH/66oB/+qpAP/qqQD/6qkA/+qpAP/pqAD/56gA/+inAP/opwD/6KYB/+imAf/lpQD/5aUA/+SjAP/kowD/5aMA/+SjAP/jogD/46IA/+KhAP/ioQD/4qAB/+GfAP/hnwD/4J4A/+CdAP/fngD/354A/96cAf/enAH/3ZsA/92aAP/cmQD/3JkA/9yZAP/bmAD/25gA/9qXAP/ZlwD/2pUA/9mZCP/kyGf/5c1w/+XMb//stR3/8K8B//CuAP/kowH/46MA/+WjAP/kowD/5KMA/+ShAP/ntC7//v////7////+/v7//v7+//7+/v/+/v7//v////7////suzb/6aQA/+qpAP/qqQD/66oB/+uqAf/rqgH/66oB/+uqAf/qqQD/6qkA/+qpAP/qqQD/6qkA/+moAP/oqAD/56cA/+inAP/opwD/6KYB/+emAf/lpQD/5aQA/+SjAP/kowD/5KMA/+OiAP/jogD/4qEA/+KhAP/ioAH/4aAB/+GfAP/hnwD/4J0A/+CdAP/fngD/350A/96cAf/enAH/3ZsA/92aAP/cmQD/3JkA/9yZAP/bmAD/25gA/9qXAP/ZlwD/2pUA/9mZCP/kyWv/5c1w/+XMb//ttR3/8K8B//CvAf/kowH/46IA/+SjAP/kowD/5KMA/+WkAP/jngD/79KB/////////////v7+//7+/v////////////LWi//oogD/6qkA/+qpAP/qqQD/6qkA/+qpAP/qqQD/6qkA/+qpAP/qqQD/6qkA/+qpAP/qqQD/6agA/+ioAP/nqAD/6KcA/+enAP/opgH/6KYB/+WlAP/lpQD/5KMA/+SjAP/lowD/5KMA/+OiAP/jogD/4qEA/+KhAP/ioAH/4aAB/+GfAP/gngD/4J0A/9+eAP/fngD/3p0A/96cAf/dmwD/3ZsA/9yaAP/cmQD/3JkA/9yZAP/bmAD/25gA/9mXAP/ZlwD/2ZUB/9mWAf/mwUz/5c93/+XMbv/tth3/8K8B//CuAf/kowH/46IA/+SjAP/lowD/5KMA/+SjAP/lpAD/458A/+/Pff/9+/T////////////9/Pf/8NOE/+ajAP/ppwD/6qkA/+qpAP/qqQD/6qkA/+qpAP/qqQD/6qkA/+qpAP/qqQD/6qkA/+moAP/pqAD/6KgA/+eoAP/opwD/56cA/+imAf/opgH/5qUA/+WlAP/lpAD/5KMA/+SjAP/kowD/5KMA/+OiAP/jogD/4qEA/+KhAP/ioAH/4aAB/+GfAP/gngD/4J0A/9+eAP/fngD/3pwB/96cAf/dmwD/3ZsA/9yZAP/cmQD/3JkA/9yZAP/bmAD/25cA/9mXAP/ZlgH/2ZUB/9qWAP/trgf/5sli/+TPev/tth3/8K8B//CuAf/kowH/46IA/+SjAP/kowD/5KMA/+SjAP/lowD/5aQA/+SeAP/orx3/7cNW/+3DV//osR//5qEA/+enAP/oqAD/6KgA/+moAP/pqAD/6qgA/+qpAP/qqQD/6qkA/+moAP/pqAD/6agA/+ioAP/nqAD/6KcA/+inAP/npwD/6KYB/+imAf/npQD/5aUA/+WkAP/kowD/5KMA/+SjAP/kowD/46IA/+OiAP/ioQD/4qEA/+KgAf/hoAH/4Z8A/+GfAP/gnQD/4J0A/9+eAP/fngD/3pwB/96cAf/dmwD/3ZsA/9yZAP/cmQD/3JkA/9yZAP/bmAD/2pcA/9mXAP/algH/2JUB/9qXAv/vrAD/7bcc/+TNcP/tth7/8K8B//CvAf/kowH/4qEA/+OiAP/kowD/5aMA/+SjAP/kowD/5aQA/+WlAP/logD/5qAA/+egAP/nowD/6KcA/+inAP/opwD/56gA/+eoAP/oqAD/6KgA/+ioAP/oqAD/6KgA/+ioAP/oqAD/56gA/+inAP/opwD/6KcA/+enAP/opgH/6KYB/+elAP/lpQD/5aUA/+WjAP/kowD/5aMA/+SjAP/kowD/46IA/+OiAP/ioQD/4qEA/+KgAf/hoAH/4Z8A/+CeAP/gnQD/354A/9+eAP/enQD/3pwB/92bAP/dmwD/3ZoA/9yZAP/cmQD/3JkA/9uYAP/bmAD/2pcA/9mXAP/algH/2JUA/9qXAv/urgL/8a8A/+2zEf/tth3/8K8B//CvAf/kogH/4qEA/+OiAP/jogD/5KMA/+WjAP/kowD/5KMA/+WkAP/lpQD/5aUA/+emAf/opgH/6KYB/+emAf/opwD/6KcA/+inAP/opwD/56cA/+ioAP/oqAD/56cA/+inAP/opwD/6KcA/+inAP/opwD/6KYB/+imAf/opgH/5qUA/+WlAP/lpQD/5aMA/+SjAP/lowD/5KMA/+SjAP/jogD/46IA/+KhAP/ioQD/4qAB/+GgAf/hnwD/4Z8A/+CdAP/gnQD/354A/9+eAP/enAH/3pwB/92bAP/dmwD/3JkA/9yZAP/cmQD/3JkA/9uYAP/bmAD/2ZcA/9mXAP/algH/2JUA/9qXAv/urgP/8a8A//CuAP/ttx3/8K8A//CvAv/kowH/4aAA/+OiAP/jogD/46IA/+SjAP/lowD/5KMA/+SjAP/lpAD/5aUA/+WlAP/mpgH/6KYB/+imAf/opgH/6KcA/+enAP/opwD/6KcA/+inAP/opwD/6KcA/+inAP/opwD/56cA/+imAf/opgH/6KYB/+emAf/mpQD/5aUA/+WkAP/kowD/5KMA/+WjAP/kowD/5KMA/+OiAP/jogD/4qEA/+KhAP/ioQD/4qAB/+GgAf/hnwD/4J4A/+CdAP/fngD/354A/9+dAP/enAH/3pwB/92bAP/dmgD/3JkA/9yZAP/cmQD/3JgA/9uYAP/alwD/2ZcA/9mWAf/ZlgH/2JUA/9qXA//urgP/8K8A//CvAf/ttxz/8K8A/++yCv/jpg3/4qAA/+KhAP/jogD/46IA/+SjAP/kowD/5aMA/+SjAP/kowD/5aMA/+WlAP/lpQD/5aUA/+emAf/opgH/6KYB/+imAf/opgH/6KYB/+imAf/opgH/6KYB/+imAf/opgH/6KYB/+imAf/npgH/5qUA/+WlAP/lpQD/5aQA/+SjAP/kowD/5aMA/+WjAP/kowD/46IA/+OiAP/ioQD/4qEA/+KhAP/ioAH/4aAB/+GfAP/hnwD/4J0A/+CdAP/fngD/354A/96cAf/enAH/3ZsA/92bAP/cmQD/3JkA/9yZAP/cmQD/25gA/9uYAP/alwD/2ZcA/9qWAf/ZlgH/2JMA/9qbDP/vsQr/8K8A//CvAP/suST/8K8A//GzCv/msir/4Z0A/+KhAP/ioQD/46IA/+OiAP/kowD/5KMA/+WjAP/kowD/5KMA/+SjAP/lpAD/5aUA/+WlAP/lpQD/5qUA/+emAf/npgH/6KYB/+imAf/opgH/6KYB/+imAf/npgH/5qUA/+alAP/lpQD/5aUA/+WkAP/lowD/5KMA/+SjAP/lowD/5aMA/+SjAP/jogD/46IA/+OiAP/ioQD/4qEA/+KgAf/ioAH/4Z8A/+GfAP/gngD/4J0A/9+eAP/fngD/3p0A/96cAf/enAH/3ZsA/92bAP/cmQD/3JkA/9yZAP/cmQD/25gA/9uYAP/ZlwD/2ZYB/9qWAf/YlgH/15AA/96pKP/xtQ3/8K4A//CxBv/suSzW8K8B//CuAP/uw0//4aEJ/+KgAP/ioQD/4qEA/+OiAP/jogD/46IA/+SjAP/kowD/5KMA/+SjAP/kowD/5KMA/+WkAP/lpQD/5aUA/+WlAP/lpQD/5aUA/+WlAP/lpQD/5aUA/+WlAP/lpQD/5aUA/+WlAP/lpAD/5aMA/+SjAP/kowD/5KMA/+WjAP/kowD/5KMA/+OiAP/jogD/46IA/+KhAP/ioQD/4qAB/+KgAf/hoAH/4Z8A/+CfAP/gnQD/354A/9+eAP/fngD/3pwB/96cAf/dmwD/3ZsA/9yaAP/cmQD/3JkA/9yZAP/bmAD/25gA/9qXAP/YlwD/2pYB/9mWAf/ZlQD/1pME/+rAUP/xsAL/8K8B/+26J/PqvkBo77AH+PCrAP/ywjn/6cFb/+CYAP/ioQD/4qEA/+KhAP/jogD/46IA/+OiAP/kowD/5KMA/+WjAP/lowD/5KMA/+SjAP/kowD/5aMA/+WkAP/lpAD/5aQA/+WkAP/lpAD/5aQA/+WkAP/lpAD/5aMA/+SjAP/kowD/5KMA/+SjAP/lowD/5KMA/+SjAP/kowD/46IA/+OiAP/ioQD/4qEA/+KhAP/ioAH/4qAB/+GgAf/hnwD/4J8A/+CdAP/gnQD/354A/9+eAP/enQD/3pwB/96cAf/dmwD/3ZsA/9yZAP/cmQD/3JkA/9yZAP/bmAD/25gA/9mXAP/ZlwD/2pYB/9mWAf/WjAD/4bZT//PFQf/wqwD/77AF++q9O4LW+v8G7bMUyPCuAP/vrAD/9NiF/+e5Sv/flgD/4qAA/+KhAP/ioQD/46IA/+OiAP/jogD/5KMA/+SjAP/kowD/5aMA/+WjAP/kowD/5KMA/+SjAP/kowD/5KMA/+SjAP/kowD/5KMA/+SjAP/kowD/5KMA/+SjAP/kowD/5aMA/+SjAP/kowD/5KMA/+OiAP/jogD/46IA/+KhAP/ioQD/4qEA/+KhAP/ioAH/4aAB/+GfAP/hnwD/4J0A/+CdAP/fngD/354A/9+dAP/enAH/3pwB/92bAP/dmwD/3JkA/9yZAP/cmQD/3JkA/9uYAP/bmAD/2pcA/9iXAP/algH/2ZUA/9WLAP/eqz//9NqM//CtAv/wrgD/7rIQ0dzSnQv///8A6rsyTO+wBf/wrQD/8LEP//fkrf/rx3L/4JwA/+CZAP/hnQD/4Z4A/+KfAP/inwD/4p8A/+OfAP/joAD/46AA/+SgAP/koAD/5KAA/+SgAP/koAD/5KAA/+SgAP/koAD/5KAA/+SgAP/koAD/5KAA/+SgAP/koAD/46AA/+OgAP/joAD/4p8A/+KfAP/inwD/4Z4A/+GeAP/hngD/4Z0A/+GdAP/gnQD/4JwA/+CcAP/fmwD/35oA/96bAP/emwD/3psA/92ZAP/dmQD/3JgA/9yYAP/clwD/25YA/9uWAP/blgD/25YA/9qVAP/alQD/2JQA/9eSAP/XjQD/1ZAA/+S8af/35bL/8bQV//CtAP/vrwT/67ovWv///wD///8A////AOy2IJvvrwP/8KwA/++wDP/34Z//9efB/+3JeP/mtDv/5a0l/+StJP/lrST/5a4k/+WuJP/lriT/5a4k/+auJP/mryT/5q8k/+avJP/mryT/5q8k/+avJP/nryT/568k/+avJP/mryT/5q8k/+avJP/mryT/5q8k/+WuJP/lriT/5a4k/+WuJP/krST/5a0k/+WtJP/krSX/5K0l/+OtJf/krCT/46wk/+OrJP/jqiX/4qok/+KrJP/iqiT/4akl/+GpJf/hqSX/4Kgk/+CoJP/fpiT/36Yk/9+mJP/fpiX/3qUl/96lJf/dpCT/3KQl/9+qOf/mwXT/8uO///jjpv/wshH/8KsA//CvAv/tth+p////AP///wD///8A////AP///wDstiKZ77AH//CtAP/vqQD/8sE9//jgnf/57MX/+e3M//nty//57cv/+e3L//rty//67cv/+e3L//nty//57cv/+u3L//rty//57cv/+e3L//nty//67cv/+u3L//nty//57cv/+e3L//nty//57cv/+e3L//rty//67cv/+e3L//nty//57cv/+u3L//rty//57cv/+e3L//nty//67cv/+e3L//nty//57cv/+e3L//nty//57cv/+e3L//nty//57cv/+e3L//nty//57cv/+ezL//nty//57cv/+e3L//nty//57cv/+e3M//nsxv/54qH/88RD/++qAP/wrAD/77AG/+y1HaK3//8B////AP///wD///8A////AP///wD///8A6boxTu2yE7zvsAjx76wA/u6pAP/vrQD/77EI/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/vsQn/77EJ/++xCf/wsQn/8LEJ//CxCf/vsQn/764A/++pAP/vrAD+77AH8u6zFcPruzJX////AP///wD///8A////AP///wD///8A////AP///wD///8A6L9HY+y4Kb7sui3767go/+y4Jf/suCX/67gl/+u4Jf/suCX/7Lgl/+u4Jf/suCX/7Lgl/+y4Jf/suCX/67gl/+u4Jf/ruCX/7Lgl/+y4Jf/ruCX/67gl/+u4Jf/suCX/7Lgl/+u4Jf/suCX/7Lgl/+y4Jf/suCX/67gl/+y4Jf/suCX/7Lgl/+y4Jf/ruCX/7Lgl/+y4Jf/ruCX/7Lgl/+y4Jf/suCX/7Lgl/+y4Jf/suCX/7Lgl/+y4Jf/ruCX/7Lcl/+y4Jf/suCX/7Lgl/+u4Jf/suCX/7Lcl/+y3Jf/ruCX/7Lgl/+y4KP/sui7967ksxui9Q2cM/wAB////AP///wD///8A////AP///wD+AAAAAAAAAH8AAAD4AAAAAAAAAB8AAADgAAAAAAAAAAcAAADAAAAAAAAAAAMAAADAAAAAAAAAAAMAAACAAAAAAAAAAAEAAACAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAACAAAAAAAAAAAEAAADAAAAAAAAAAAMAAADAAAAAAAAAAAMAAADgAAAAAAAAAAcAAAD4AAAAAAAAAB8AAAD+AAAAAAAAAH8AAAA="

if getattr(sys, 'frozen', False):
    _PASTA_EXE = os.path.dirname(sys.executable)
else:
    _PASTA_EXE = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_VERSAO = os.path.join(_PASTA_EXE, "versao_instalada.json")

QUERY = """
query GetDownloads {
  categorias {
    nome
    links {
      nome
      nome_link_arquivo
      versao
      ordem_listagem
      url
    }
  }
}
"""

class WorkerAtualizacao(QThread):
    progresso = pyqtSignal(int)
    status = pyqtSignal(str)
    finalizado = pyqtSignal(bool, str)

    def run(self):
        try:
            log.info("="*50)
            log.info("Iniciando processo de atualização")

            self.status.emit("Buscando versão estável no servidor...")
            log.info("Consultando API para versão estável...")
            url, nome_arquivo, versao_nova = self.obter_dados_api()
            
            if not versao_nova:
                log.error("Versão estável não encontrada na API")
                self.finalizado.emit(False, "Versão estável não encontrada na API.")
                return
            log.info(f"Versão encontrada no servidor: {versao_nova}")

            versao_cache = self.obter_versao_cache()
            log.info(f"Versão no cache local: {versao_cache}")
            if versao_cache and versao_nova == versao_cache:
                log.info("Versão cache igual à do servidor. Já atualizado.")
                self.finalizado.emit(False, "O sistema já está atualizado.")
                return

            self.status.emit("Verificando versão instalada...")
            versao_local = self.obter_versao_instalada()
            log.info(f"Versão instalada no registro: {versao_local}")

            if versao_nova == versao_local:
                log.info("Versão instalada igual à do servidor. Atualizando cache.")
                self.salvar_versao_cache(versao_nova)
                self.finalizado.emit(False, "O sistema já está atualizado.")
                return

            self.status.emit("Fechando InovaFarma...")
            log.info("Fechando processos do InovaFarma...")
            self.fechar_sistema()

            self.status.emit(f"Baixando versão {versao_nova}...")
            log.info(f"Iniciando download: {url}")
            caminho_exe = self.baixar_com_progresso(url, nome_arquivo)
            
            if not caminho_exe:
                log.error("Falha ao baixar o instalador")
                self.finalizado.emit(False, "Falha ao baixar o instalador.")
                return
            log.info(f"Download concluído: {caminho_exe}")

            # Verificar se o arquivo baixado tem tamanho razoável
            tamanho_arquivo = os.path.getsize(caminho_exe)
            log.info(f"Tamanho do instalador: {tamanho_arquivo / (1024*1024):.1f} MB")
            if tamanho_arquivo < 1024 * 100:  # menor que 100KB provavelmente corrompido
                log.error(f"Arquivo muito pequeno ({tamanho_arquivo} bytes), possível download corrompido")
                self.finalizado.emit(False, "Download do instalador incompleto. Tente novamente.")
                return

            self.status.emit("Solicitando permissão de administrador...")
            params = '/exenoui /qn'
            caminho_limpo = os.path.normpath(caminho_exe)
            log.info(f"Executando instalador: {caminho_limpo} {params}")
            
            resultado_admin = ctypes.windll.shell32.ShellExecuteW(None, "runas", caminho_limpo, params, None, 1)
            log.info(f"ShellExecuteW retornou: {resultado_admin}")
            
            if resultado_admin <= 32:
                log.error(f"Falha ao executar como admin. Código: {resultado_admin}")
                raise Exception("O usuário recusou a permissão de administrador.")

            self.status.emit("Instalando... Por favor, não abra o sistema.")
            nome_processo = os.path.basename(caminho_limpo)
            log.info(f"Aguardando processo do instalador: {nome_processo}")
            
            # Aguardar o processo iniciar
            time.sleep(5)
            
            # Monitorar instalação COM TIMEOUT
            inicio_instalacao = time.time()
            processo_encontrado = False
            iteracoes = 0
            
            while True:
                tempo_decorrido = time.time() - inicio_instalacao
                iteracoes += 1
                
                if tempo_decorrido > TIMEOUT_INSTALACAO:
                    log.warning(f"Timeout de instalação atingido ({TIMEOUT_INSTALACAO}s). Continuando...")
                    break
                
                time.sleep(3)
                rodando = False
                try:
                    for proc in psutil.process_iter(['name', 'pid']):
                        try:
                            nome = proc.info['name']
                            if nome and nome.lower() == nome_processo.lower():
                                rodando = True
                                if not processo_encontrado:
                                    log.info(f"Processo encontrado: {nome} (PID: {proc.info['pid']})")
                                    processo_encontrado = True
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                except Exception as e:
                    log.warning(f"Erro ao listar processos (iteração {iteracoes}): {e}")
                
                if not rodando and processo_encontrado:
                    log.info(f"Instalador finalizado após {tempo_decorrido:.0f}s")
                    break
                
                # Se após 60s o processo nunca foi encontrado, provavelmente já terminou
                if not processo_encontrado and tempo_decorrido > 60:
                    log.warning("Processo do instalador nunca foi encontrado. Pode ter finalizado rapidamente.")
                    break
                
                # Log periódico a cada 30s
                if iteracoes % 10 == 0:
                    log.debug(f"Aguardando instalação... ({tempo_decorrido:.0f}s, rodando={rodando})")

            # Pequena pausa para garantir que MSI terminou completamente
            time.sleep(3)

            self.status.emit("Ajustando atalhos do Windows...")
            log.info("Corrigindo atalhos da barra de tarefas...")
            self.corrigir_atalhos_barra_tarefas()

            self.salvar_versao_cache(versao_nova)
            log.info(f"Cache atualizado para versão {versao_nova}")
            
            self.status.emit("Iniciando InovaFarma...")
            log.info("Abrindo InovaFarma...")
            self.abrir_sistema()
            
            log.info(f"Atualização concluída com sucesso! Versão: {versao_nova}")
            self.finalizado.emit(True, f"Sucesso! A versão {versao_nova} foi instalada com êxito.")

        except Exception as e:
            log.exception(f"Erro inesperado durante atualização: {e}")
            self.finalizado.emit(False, f"Erro inesperado: {str(e)}")

    def obter_versao_cache(self):
        try:
            with open(ARQUIVO_VERSAO, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                return dados.get('versao')
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def salvar_versao_cache(self, versao):
        try:
            with open(ARQUIVO_VERSAO, 'w', encoding='utf-8') as f:
                json.dump({'versao': versao}, f)
        except Exception:
            pass

    def corrigir_atalhos_barra_tarefas(self):
        ps_script = """
        $path = "$env:APPDATA\\Microsoft\\Internet Explorer\\Quick Launch\\User Pinned\\TaskBar"
        if (Test-Path $path) {
            $shell = New-Object -ComObject WScript.Shell
            Get-ChildItem -Path $path -Filter "*.lnk" | ForEach-Object {
                $shortcut = $shell.CreateShortcut($_.FullName)
                if ($shortcut.TargetPath -match "InovaFarma") {
                    $target = $shortcut.TargetPath
                    $shortcut.TargetPath = $target
                    $shortcut.Save()
                }
            }
        }
        """
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], creationflags=0x08000000)
        except Exception:
            pass

    def obter_versao_instalada(self):
        locais = [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                  (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")]
        for hive, caminho in locais:
            try:
                chave = winreg.OpenKey(hive, caminho)
                for i in range(winreg.QueryInfoKey(chave)[0]):
                    try:
                        sub_nome = winreg.EnumKey(chave, i)
                        with winreg.OpenKey(chave, sub_nome) as sk:
                            nome = winreg.QueryValueEx(sk, "DisplayName")[0]
                            if NOME_SISTEMA_BUSCA.lower() in nome.lower():
                                return winreg.QueryValueEx(sk, "DisplayVersion")[0]
                    except:
                        continue
            except: continue
        return "0.0.0.0"

    def obter_dados_api(self):
        tentativas = 3
        for tentativa in range(1, tentativas + 1):
            try:
                log.debug(f"API tentativa {tentativa}/{tentativas}")
                r = requests.post(URL_API, json={"query": QUERY}, timeout=20)
                r.raise_for_status()
                dados = r.json()
                log.debug(f"Resposta API: status={r.status_code}")
                categorias = dados.get('data', {}).get('categorias', [])
                for cat in categorias:
                    if cat.get('nome') == "Versões INOVAFARMA":
                        links = cat.get('links', [])
                        for link in links:
                            if link.get('ordem_listagem') == 1 and link.get('url', '').endswith('.exe'):
                                url = link.get('url')
                                nome = link.get('nome_link_arquivo')
                                versao = link.get('versao')
                                log.info(f"Dados API: versao={versao}, arquivo={nome}")
                                return url, nome, versao
                log.warning("Categoria 'Versões INOVAFARMA' ou link estável não encontrado")
                return None, None, None
            except requests.exceptions.Timeout:
                log.warning(f"Timeout na API (tentativa {tentativa})")
            except requests.exceptions.ConnectionError:
                log.warning(f"Erro de conexão com API (tentativa {tentativa})")
            except Exception as e:
                log.error(f"Erro na API (tentativa {tentativa}): {e}")
            if tentativa < tentativas:
                time.sleep(3)
        log.error("Todas as tentativas de acesso à API falharam")
        return None, None, None

    def baixar_com_progresso(self, url, nome):
        path = os.path.join(tempfile.gettempdir(), nome)
        if os.path.exists(path):
            try:
                os.remove(path)
                log.debug(f"Arquivo anterior removido: {path}")
            except Exception as e:
                log.warning(f"Não foi possível remover arquivo anterior: {e}")
        try:
            r = requests.get(url, stream=True, timeout=(15, TIMEOUT_DOWNLOAD))
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            log.info(f"Download iniciado. Tamanho total: {total / (1024*1024):.1f} MB")
            baixado = 0
            ultimo_log = time.time()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        baixado += len(chunk)
                        if total > 0:
                            self.progresso.emit(int((baixado / total) * 100))
                        # Log a cada 10 segundos
                        agora = time.time()
                        if agora - ultimo_log >= 10:
                            log.debug(f"Download: {baixado / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB")
                            ultimo_log = agora
            log.info(f"Download concluído: {baixado} bytes")
            return path
        except requests.exceptions.Timeout:
            log.error("Timeout durante download do instalador")
            return None
        except requests.exceptions.ConnectionError:
            log.error("Erro de conexão durante download")
            return None
        except Exception as e:
            log.error(f"Erro durante download: {e}")
            return None

    def fechar_sistema(self):
        nome_executavel = "InovaFarma.exe"
        processos_fechados = 0
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == nome_executavel.lower():
                    log.info(f"Fechando {proc.info['name']} (PID: {proc.info['pid']})")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        log.warning(f"Forçando kill do PID {proc.info['pid']}")
                        proc.kill()
                    processos_fechados += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                log.debug(f"Erro ao fechar processo: {e}")
                continue
        log.info(f"Processos InovaFarma fechados: {processos_fechados}")

    def abrir_sistema(self):
        caminho_exe = r"C:\InovaFarma\InovaFarma.exe"
        if os.path.exists(caminho_exe):
            try:
                subprocess.Popen([caminho_exe], cwd=os.path.dirname(caminho_exe))
                log.info(f"InovaFarma iniciado: {caminho_exe}")
            except Exception as e:
                log.error(f"Erro ao iniciar InovaFarma: {e}")
        else:
            log.warning(f"Executável não encontrado: {caminho_exe}")

class JanelaAtualizador(QMainWindow):
    def __init__(self):
        super().__init__()
        self.configurar_ui()
        self.iniciar_processo()

    def configurar_ui(self):
        self.setWindowTitle("Atualizador InovaFarma")
        self.setFixedSize(450, 240) 
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        # Estilo Moderno e Confiante
        self.setStyleSheet("""
            JanelaAtualizador {
                background-color: #f7f9fc;
            }
            QLabel {
                color: #2b3643;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel#Logo {
                margin-top: 15px;
            }
            QLabel#Status {
                font-size: 11pt;
                font-weight: 500;
                color: #3b4b5c;
                margin-bottom: 5px;
            }
            QProgressBar {
                border: none;
                background-color: #e2e8f0;
                border-radius: 6px;
                height: 12px;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0078D4, stop:1 #00BCF2);
                border-radius: 6px;
            }
        """)

        Img_data = QByteArray.fromBase64(LOGO_BASE64.encode())
        pixmap = QPixmap()
        pixmap.loadFromData(Img_data)
        self.setWindowIcon(QIcon(pixmap))

        central = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setSpacing(15)
        
        self.lbl_logo = QLabel()
        self.lbl_logo.setObjectName("Logo")
        self.lbl_logo.setPixmap(pixmap.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_status = QLabel("Iniciando processo...")
        self.lbl_status.setObjectName("Status")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setWordWrap(True)
        
        self.barra_progresso = QProgressBar()
        self.barra_progresso.setTextVisible(False)

        layout.addStretch()
        layout.addWidget(self.lbl_logo)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.barra_progresso)
        layout.addStretch()
        
        central.setLayout(layout)
        self.setCentralWidget(central)

    def iniciar_processo(self):
        self.worker = WorkerAtualizacao()
        self.worker.progresso.connect(self.atualizar_progresso)
        self.worker.status.connect(self.atualizar_status)
        self.worker.finalizado.connect(self.concluir)
        self.worker.start()

    def atualizar_progresso(self, valor):
        if self.barra_progresso.maximum() == 0:
            self.barra_progresso.setMaximum(100)
        self.barra_progresso.setValue(valor)

    def atualizar_status(self, texto):
        self.lbl_status.setText(texto)
        # Barra indeterminada durante instalação (sem % definido)
        if "Instalando" in texto:
            self.barra_progresso.setMaximum(0)  # modo indeterminado (animação)
        elif "Baixando" not in texto:
            self.barra_progresso.setMaximum(100)

    def concluir(self, sucesso, mensagem):
        log.info(f"Finalizado: sucesso={sucesso}, msg={mensagem}")
        if not sucesso and mensagem != "O sistema já está atualizado.":
            QMessageBox.warning(self, "Atualização", mensagem)
        sys.exit()

def configurar_inicializacao():
    try:
        caminho_app = os.path.realpath(sys.argv[0])
        nome_tarefa = "InovaFarmaUpdaterTask"
        comando_agendador = (
            f'schtasks /create /tn "{nome_tarefa}" /tr "\\"{caminho_app}\\"" '
            f'/sc onlogon /rl highest /f'
        )
        subprocess.run(comando_agendador, shell=True, capture_output=True)
    except Exception as e:
        print(f"Erro ao agendar tarefa: {e}")

def verificar_cache_rapido():
    """Verifica se a versão do site já é a mesma do cache, sem abrir janela."""
    try:
        with open(ARQUIVO_VERSAO, 'r', encoding='utf-8') as f:
            versao_cache = json.load(f).get('versao')
        if not versao_cache:
            return False
        r = requests.post(URL_API, json={"query": QUERY}, timeout=15)
        categorias = r.json().get('data', {}).get('categorias', [])
        for cat in categorias:
            if cat.get('nome') == "Versões INOVAFARMA":
                for link in cat.get('links', []):
                    if link.get('ordem_listagem') == 1 and link.get('url', '').endswith('.exe'):
                        return link.get('versao') == versao_cache
    except Exception:
        pass
    return False

if __name__ == "__main__":
    log.info("Atualizador iniciado")
    app = QApplication(sys.argv)
    configurar_inicializacao()
    if verificar_cache_rapido():
        log.info("Cache indica que já está atualizado. Saindo.")
        sys.exit(0)
    janela = JanelaAtualizador()
    janela.show()
    sys.exit(app.exec())