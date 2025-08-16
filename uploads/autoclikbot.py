from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import random

# Configurações do Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")  # modo invisível, se quiser
chrome_options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=chrome_options)
driver.get("https://www.tiktok.com/@usuario/live")

time.sleep(5)  # espera a página carregar

try:
    # Localiza o botão de like (exemplo, precisa inspecionar a live real)
    like_button = driver.find_element(By.XPATH, "//button[contains(@class,'like-button')]")
    
    # Simula clique humano
    like_button.click()
    time.sleep(random.uniform(1, 3))  # delay aleatório
except:
    print("Botão não encontrado ou live ainda não carregou")
