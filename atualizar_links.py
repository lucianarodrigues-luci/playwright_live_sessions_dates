# atualizar_links.py
import os
import re
import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

load_dotenv()
LW_EMAIL = os.getenv("LW_EMAIL")
LW_PASSWORD = os.getenv("LW_PASSWORD")
LW_LOGIN_URL = os.getenv("LW_LOGIN_URL", "https://training.tergar.org/author")
CSV_PATH = "dados.csv"


def login(page):
    page.goto(LW_LOGIN_URL)
    page.wait_for_selector("input[id='email']")
    page.fill("input[id='email']", LW_EMAIL)
    page.fill("input[id='password']", LW_PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_timeout(2500)
    print("✅ Login realizado.")


def editar_card_date_time(page, trainer_label, date_time_text):
    print(f"   🔎 Procurando Trainer: {trainer_label}")

    # 1) entra no iframe do editor
    frame = page.frame_locator("iframe#pageseditorIframe")

    # 2) acha o bloco do Trainer dentro do frame
    trainer_block = None
    try:
        trainer_block = frame.locator(
            "div.lw-ebook-mainTextNormal[contenteditable]"
        ).filter(has_text=trainer_label).first
        trainer_block.wait_for(timeout=5000)
    except PWTimeoutError:
        trainer_block = None

    if trainer_block is None or trainer_block.count() == 0:
        raise RuntimeError(f"Trainer não encontrado: {trainer_label}")

    trainer_block.scroll_into_view_if_needed()
    page.wait_for_timeout(150)

    # 3) sobe ao container do card
    try:
        card_container = trainer_block.locator(
            "xpath=ancestor::div[contains(@class,'learnworlds-element')][1]"
        )
        if card_container.count() == 0:
            card_container = trainer_block
    except Exception:
        card_container = trainer_block

    # 4) acha o "Date and time" no mesmo card
    date_block = None
    try:
        date_block = card_container.locator(
            "div.lw-ebook-mainTextNormal[contenteditable]"
        ).filter(has_text="Date and time").first
        date_block.wait_for(timeout=4000)
    except PWTimeoutError:
        date_block = None

    if date_block is None or date_block.count() == 0:
        raise RuntimeError(f"'Date and time' não encontrado no card de {trainer_label}")

    date_block.scroll_into_view_if_needed()
    page.wait_for_timeout(120)

    # 5) edita o texto
    try:
        date_block.click()
        page.wait_for_timeout(80)
        date_block.fill(f"Date and time: {date_time_text}")
    except Exception:
        try:
            page.keyboard.press("Meta+a")
        except Exception:
            page.keyboard.press("Control+A")
        page.keyboard.type(f"Date and time: {date_time_text}")

    print(f"   ✅ {trainer_label} → {date_time_text}")


def salvar_pagina(page):
    """
    Dá SAVE uma vez por Section/page:
    - clica no botão Save (topbar)
    - se aparecer popup "You are changing synced content", marca checkbox e clica Save no popup
    """
    frame = page.frame_locator("iframe#pageseditorIframe")
    salvou = False

    print("   💾 Salvando alterações da página...")

    # 1) tenta clicar no Save dentro do iframe (topbar do editor)
    for sel in [
        "button.js-topbar-save",
        "button.btn.js-topbar-save",
        "button:has-text('Save')",
    ]:
        try:
            loc = frame.locator(sel).first
            if loc.count() > 0:
                loc.click(timeout=4000)
                print(f"   👉 Clique em Save (iframe, seletor {sel}) enviado.")
                salvou = True
                break
        except Exception:
            continue

    # 2) fallback: por role/name com regex
    if not salvou:
        try:
            frame.get_by_role(
                "button",
                name=re.compile("save", re.IGNORECASE)
            ).first.click(timeout=4000)
            print("   👉 Clique em Save (iframe, get_by_role regex) enviado.")
            salvou = True
        except Exception:
            pass

    if not salvou:
        print("   ⚠️ Não consegui clicar no Save dentro do iframe.")
        return False

    # pequeno tempo pro popup aparecer, se for o caso
    page.wait_for_timeout(300)

    # 3) procura popup global "You are changing synced content"
    popup = None
    try:
        popup = page.locator("div.learnworlds-popup-window-wrapper").filter(
            has_text=re.compile("You are changing synced content", re.IGNORECASE)
        ).first
        popup.wait_for(timeout=2500)
    except PWTimeoutError:
        popup = None

    if popup is not None and popup.count() > 0:
        print("   ⚠️ Popup 'You are changing synced content' detectado.")

        # 3.1) marca o checkbox de confirmação
        checkbox_marcado = False
        try:
            popup.locator("input.lw-checkbox-input[name='confirmation']").first.check(
                force=True, timeout=1500
            )
            checkbox_marcado = True
            print("   ☑️ Checkbox marcado (input.lw-checkbox-input[name='confirmation']).")
        except Exception:
            try:
                popup.locator("label:has(input.lw-checkbox-input[name='confirmation'])").first.click(
                    timeout=1500
                )
                checkbox_marcado = True
                print("   ☑️ Checkbox marcado clicando no <label>.")
            except Exception:
                print("   ⚠️ Não consegui marcar o checkbox do popup.")

        # 3.2) clica no botão Save do popup
        save_modal_clicado = False
        try:
            popup.get_by_role(
                "button",
                name=re.compile("save", re.IGNORECASE)
            ).first.click(timeout=2000)
            save_modal_clicado = True
            print("   💾 Clique em Save do popup (get_by_role) enviado.")
        except Exception:
            try:
                popup.locator("button:has-text('Save')").first.click(timeout=2000)
                save_modal_clicado = True
                print("   💾 Clique em Save do popup (has-text) enviado.")
            except Exception:
                print("   ⚠️ Não consegui clicar no Save do popup.")

        # 3.3) aguarda fechamento do popup
        if save_modal_clicado:
            try:
                popup.wait_for(state="detached", timeout=3000)
                print("   ✅ Popup fechado após salvar.")
            except Exception:
                print("   ℹ️ Popup não se desprendeu (pode ser normal).")
    else:
        print("   ✅ Nenhum popup de conteúdo sincronizado.")

    # 4) espera toast de sucesso ou dá delay
    try:
        frame.locator(".toast-success, .lw-toast--success").first.wait_for(timeout=2500)
        print("   🎉 Toast de sucesso detectado.")
    except Exception:
        page.wait_for_timeout(800)
        print("   ⏳ Sem toast detectado, usando pequeno delay.")

    print("   💾 Página salva com sucesso.")
    return True


def main():
    df = pd.read_csv(CSV_PATH)
    df.columns = [c.lower() for c in df.columns]

    if "status" in df.columns:
        df = df[df["status"].astype(str).str.lower() == "pronto"]

    required = {"trainer_label", "section", "session_url", "date_time"}
    if not required.issubset(set(df.columns)):
        raise SystemExit(f"❌ CSV inválido. Esperado: {required}, encontrado: {set(df.columns)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        login(page)

        for session_url, group in df.groupby("session_url"):
            print(f"\n➡️ Abrindo Section: {session_url}")
            page.goto(session_url)
            page.wait_for_timeout(1700)

            # toque de scroll pra garantir que todos os cards renderizem
            try:
                page.mouse.wheel(0, 99999)
                page.wait_for_timeout(250)
                page.mouse.wheel(0, -99999)
                page.wait_for_timeout(150)
            except Exception:
                pass

            # 1) edita todos os trainers dessa página
            for _, row in group.iterrows():
                trainer = str(row["trainer_label"]).strip()
                dt = str(row["date_time"]).strip()
                if not trainer or not dt:
                    print("   ⚠️ Linha ignorada (trainer/date_time vazios)")
                    continue
                try:
                    editar_card_date_time(page, trainer, dt)
                except Exception as e:
                    print(f"   ❌ Falha em {trainer}: {e}")

            # 2) uma chamada de Save por página
            salvar_pagina(page)

        print("\n🎉 Concluído.")
        browser.close()


if __name__ == "__main__":
    main()
