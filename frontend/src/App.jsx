import React, { useEffect, useState } from "react";

const API = "/api/v1";
const tg = window.Telegram?.WebApp;

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Telegram-Init-Data": tg?.initData || "",
    ...(options.headers || {})
  };

  const res = await fetch(API + path, {...options, headers});
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || "Ошибка запроса");
  }
  return data;
}

export default function App() {
  const [tab, setTab] = useState("home");
  const [me, setMe] = useState(null);
  const [plans, setPlans] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api("/me"),
      api("/sherlock/plans"),
      api("/subscriptions")
    ])
      .then(([m, p, s]) => {
        setMe(m);
        setPlans(p);
        setSubscriptions(s);
      })
      .catch(e => setError(e.message));
  }, []);

  async function buy(planId) {
    try {
      setError("");
      const data = await api(`/sherlock/invoice?plan_id=${planId}`, {
        method: "POST"
      });

      if (tg?.openInvoice) {
        tg.openInvoice(data.invoice_url, (status) => {
          if (status === "paid") {
            api("/subscriptions")
              .then(setSubscriptions)
              .catch(() => {});
            tg?.showPopup?.({
              title: "ISK",
              message: "Оплата подтверждена. Подписка активирована.",
              buttons: [{type: "ok"}]
            });
          }
        });
      } else {
        window.open(data.invoice_url, "_blank");
      }
    } catch (e) {
      setError(e.message);
    }
  }

  async function runSherlock() {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setAnswer("");

    try {
      const data = await api("/sherlock/query", {
        method: "POST",
        body: JSON.stringify({query})
      });
      setAnswer(data.answer);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const activeSub = subscriptions.find(
    x => x.service === "sherlock" && x.status === "active"
  );

  return (
    <div className="app">
      <header>
        <div className="logo">ISK</div>
        <div className="user">
          {me?.first_name || "User"}
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      {tab === "home" && (
        <main>
          <section className="hero">
            <span>МУЛЬТИСЕРВИС</span>
            <h1>Все нужное<br/>в одном месте.</h1>
            <p>ISK — единая точка доступа к сервисам и подпискам.</p>
          </section>

          <Card
            icon="🕵️"
            title="Sherlock"
            text={activeSub ? `Тариф ${activeSub.plan.toUpperCase()}` : "Базовый доступ"}
            onClick={() => setTab("sherlock")}
          />

          <Card
            icon="🌐"
            title="Network"
            text="VPN / Proxy"
            onClick={() => setError("Network подключается следующим модулем.")}
          />

          <Card
            icon="🛒"
            title="Market"
            text="Цифровые товары"
            onClick={() => setError("Market подключается следующим модулем.")}
          />
        </main>
      )}

      {tab === "sherlock" && (
        <main>
          <h2>🕵️ Sherlock</h2>
          <p className="muted">
            {activeSub
              ? `Активный тариф: ${activeSub.plan.toUpperCase()}`
              : "FREE"}
          </p>

          <div className="query">
            <textarea
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Введите запрос..."
              maxLength={2000}
            />
            <button onClick={runSherlock} disabled={loading}>
              {loading ? "Обработка..." : "Запустить"}
            </button>
          </div>

          {answer && (
            <div className="answer">
              <pre>{answer}</pre>
            </div>
          )}

          <h3>Тарифы</h3>
          {plans.filter(x => x.slug !== "free").map(plan => (
            <div className="plan" key={plan.id}>
              <div>
                <b>{plan.name}</b>
                <p>{plan.description}</p>
                <small>{plan.duration_days} дней</small>
              </div>
              <button onClick={() => buy(plan.id)}>
                {plan.price_stars} ⭐
              </button>
            </div>
          ))}
        </main>
      )}

      {tab === "profile" && (
        <main>
          <h2>👤 Профиль</h2>
          <div className="profile">
            <div>ID</div>
            <b>{me?.telegram_id}</b>
            <div>Username</div>
            <b>{me?.username ? "@" + me.username : "—"}</b>
            <div>Sherlock</div>
            <b>{me?.sherlock_plan?.toUpperCase()}</b>
          </div>

          <h3>Подписки</h3>
          {subscriptions.length === 0 && <p className="muted">Пока нет подписок.</p>}
          {subscriptions.map((s, i) => (
            <div className="subscription" key={i}>
              <b>{s.service}</b>
              <span>{s.plan}</span>
              <small>{new Date(s.expires_at).toLocaleString()}</small>
            </div>
          ))}
        </main>
      )}

      <nav>
        <button className={tab === "home" ? "active" : ""} onClick={() => setTab("home")}>⌂<span>Главная</span></button>
        <button className={tab === "sherlock" ? "active" : ""} onClick={() => setTab("sherlock")}>🕵️<span>Sherlock</span></button>
        <button onClick={() => setError("Network скоро будет подключен.")}>🌐<span>Network</span></button>
        <button onClick={() => setError("Market скоро будет подключен.")}>🛒<span>Market</span></button>
        <button className={tab === "profile" ? "active" : ""} onClick={() => setTab("profile")}>👤<span>Профиль</span></button>
      </nav>
    </div>
  );
}

function Card({icon, title, text, onClick}) {
  return (
    <button className="card" onClick={onClick}>
      <div className="card-icon">{icon}</div>
      <div>
        <b>{title}</b>
        <p>{text}</p>
      </div>
      <strong>→</strong>
    </button>
  );
}
