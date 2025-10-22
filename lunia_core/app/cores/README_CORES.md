# Lunia Cores Runtime (Overview)

Эта директория содержит асинхронный рантайм для модульных «ядер» Lunia. Реализация
сфокусирована на том, чтобы предоставить единый способ управления жизненным циклом ядра,
приёма сигналов и публикации статуса наружу через REST API.

Основные компоненты:

* `runtime/` — базовые классы `BaseCore`, реестр `CoreRegistry`, супервизор `CoreSupervisor`
  и circuit breaker.
* `impl/` — минимальные реализации ядер (SPOT, HFT, Futures, Options, Arbitrage, DeFi, LLM).
* `signals/` — типы сигналов, pub/sub-шина и лимитер.
* `api/` — Flask blueprint (и optional FastAPI router) для управления ядрами.
* `monitoring/` — вспомогательные утилиты для healthcheck (минимально).
* `tests/` — smoke/юнит тесты для проверки регистрации и REST маршрутов.

## Быстрый старт

```bash
# Запрос списка ядер
curl -s http://localhost:8080/api/v1/cores/ | jq .

# Включить/выключить ядро
curl -sX POST http://localhost:8080/api/v1/cores/SPOT/toggle \
  -H "Content-Type: application/json" -d '{"enabled": true}'
```

## Расширение

* Новые ядра добавляются путём наследования `BaseCore` и регистрации в
  `CORE_FACTORY` (см. `runtime/registry.py`).
* Для интеграции с LLM сигналы должны быть совместимы с моделью `SignalRequest`
  из `api/models.py`.
* Blueprint можно подключить к существующему Flask приложению через
  `app.register_blueprint(cores_bp, url_prefix="/api/v1")`.

Документ служит стартовой точкой; подробные инструкции могут быть дополнены в будущем.
