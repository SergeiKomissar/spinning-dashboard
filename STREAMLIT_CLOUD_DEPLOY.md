# Деплой на Streamlit Cloud

## Шаг 1: Создать репозиторий на GitHub

1. Зайдите на https://github.com
2. Нажмите **"New repository"**
3. Название: `spinning-dashboard`
4. Тип: **Private** (приватный)
5. Нажмите **"Create repository"**

## Шаг 2: Загрузить код на GitHub

Откройте терминал в папке Dashboard и выполните:

```bash
cd /Users/komissarov/DashboardPVV/Dashboard

# Инициализируем git (если ещё нет)
git init

# Добавляем все файлы (кроме секретов - они в .gitignore)
git add .

# Коммитим
git commit -m "Initial commit"

# Подключаем GitHub (замените YOUR_USERNAME на ваш логин)
git remote add origin https://github.com/YOUR_USERNAME/spinning-dashboard.git

# Загружаем
git branch -M main
git push -u origin main
```

## Шаг 3: Настроить Streamlit Cloud

1. Зайдите на https://share.streamlit.io
2. Войдите через GitHub
3. Нажмите **"New app"**
4. Выберите:
   - Repository: `spinning-dashboard`
   - Branch: `main`
   - Main file path: `app/dashboard.py`
5. Нажмите **"Advanced settings"**

## Шаг 4: Добавить Secrets

В **Advanced settings** → **Secrets** вставьте:

```toml
# Google Service Account credentials
[gcp_service_account]
type = "service_account"
project_id = "dashboardpy-446710"
private_key_id = "e47304c8b1a3b1fe585d65faf115a3017eb9860a"
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCxXWo5xSQ56sqb\ncMl6MFxYpyhgqVYupEgysguZY304d6UMPRoraWoi8/WvAjl5aDa8Y769y/nhT3G6\nNvsmBGrODU+jaQ4xjke5R63Yt3cOl73v41lIe37GRlMpi2E6wf/xGOS5qIP5BuCD\nJVrX09lndjExDlnqDV3GPImejXj3Nv6nEoJAIP1APuFZO6Y4tRCB+AmUXvhGhr5z\nUV4YgIOt4jWfJ7mnd9L7FrvnQ4JzI+LBY4qgph/BHSZojb+kqIKyWkBWvRxT83fA\nBf0JN6q1VGCb/ZDzClRfelBPGzX7FAI+9xCs9g7ztmhOBixJFJEkF8NgUYXt70Dw\n0p8u/9OFAgMBAAECggEAV6I9Qw/6BzfQJZ9DnUDZz9+/norsjx0SoyG/g2lZzJWp\nEfP6wypRi7WYVYE23pq0OL7b1rE65K05FvXlf3I9R1PiXm4g2jFflNcquWJky+wD\np8xgJ+UEzXifzG4We06xY/GVyXnOwzM3qPTC/tKon2sRgRiDKpayF6l/obxq4VIS\nMlP0T5PJeBNHUpsdgsCT7jBFtZoGJXuhECrSmgns1ijo5QKTuwFLlvaRQu7IWudz\nn3IPG4EUT7L2cR0XO99GOobhwnn+E6GcewbW+eSyV2fYlHRjtN9QR+V/fKEX0WAr\n1+9qR7mI1C/kmXuJEdmMxQG+s2b1bCM2L5j3N6tUvQKBgQDsDEg1bXAEqp6eKe0X\nd80zqCkGHVU8Rw151G6lkgkRmsnoOdQzAcY7KkCJyjaw+S5mIBiKjLyAFjEMsUxE\n+J/Adage2QKwFkTvOu0RPNp//yYp80yy82fzXdd3RAadyR5MkYyilTpU41+H8JEl\nosGPMmQ68z20HV9+mFhUsuyEhwKBgQDAW1IaIl+wvrLy4sI+SePZWbFBs3TwoZfg\nEUbNlGaFJpnIxH5QiOyO52AGYdSvLubxmyselQOUg6TL2a5/lvoTpTnzkCaeQacq\nBBg/wsDDXYPDV29BTVlNwwgCIQvY2oNXdFNNvaO0U4yjVjDJOdfII9IJPDrQDw9z\nxUr70vr2kwKBgCGWGcwoVzECyfD9TDPzoun/ul6ZW+Box70XAetjHRE5MhNt7wiW\n7wrKF0bD1AZYXka/uF42ajfbcH062PxTV/+9ff9tp1lAwew8OTEjtH9T4a1EZhxs\nT9Ur/BWHQ12+GSaR6y3TB+q+M4CXNT/iqaHjbKmKpLP1HfpYWPEsSEUPAoGAAc4Z\nlCM0cK0pcrwMBJee6sA7uJkdhNCPY0vmNTGqUJ+PG+I0KT9PsPuc3BJ483fmNOg2\n3F+bm/4sQrl1OL9K83o+c/mrUxrcnblSHO8P7gVnoiKk6aD3MJKe9Z4nxU4vo1d1\nHKql6aBLFpFNfeXsD3W+l9WX27H4fCai0IAnWL8CgYBvHXMmaCN4msAu4KqAYk9h\nC6c39YgdP7GKXrcLiH8njPSl1Snh9XqAPWH+vDU3+1nOGSY2E8H+qY6brixw0Wih\neaqWv97WcaLyLViXSs0Zyvjg+lbWhq9ytJov1f12tIgYirARo3uUSMmLx6xkPrDa\nrfbg8wCV9N1IRWofHxGvJw==\n-----END PRIVATE KEY-----\n"
client_email = "statpryd2025@dashboardpy-446710.iam.gserviceaccount.com"
client_id = "109762667407603726569"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/statpryd2025%40dashboardpy-446710.iam.gserviceaccount.com"

# Пользователи
[users.credentials.usernames.sergeikomissarov]
name = "Сергей Комиссаров"
password = "291977"
role = "admin"

[users.credentials.usernames.ivangoloti]
name = "Иван Голоти"
password = "847362"
role = "user"

[users.credentials.usernames.sergeipivovarov]
name = "Сергей Пивоваров"
password = "529164"
role = "user"

[users.credentials.usernames.alexanderzlobin]
name = "Александр Злобин"
password = "673918"
role = "user"

[users.cookie]
expiry_days = 30
key = "spinning_dashboard_secret_key_2024"
name = "spinning_dashboard_auth"
```

## Шаг 5: Запустить приложение

1. Нажмите **"Deploy!"**
2. Подождите 2-3 минуты пока развернётся
3. Получите URL типа: `https://spinning-dashboard.streamlit.app`

## Готово!

Теперь дашборд работает 24/7 в облаке. Можно выключать ноутбук.

---

## Обновление приложения

После изменений в коде:

```bash
cd /Users/komissarov/DashboardPVV/Dashboard
git add .
git commit -m "Update description"
git push
```

Streamlit Cloud автоматически обновит приложение через 1-2 минуты.
