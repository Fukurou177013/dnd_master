import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, ApiError } from "./api";
import type { Campaign, Character } from "./types";

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Не удалось выполнить запрос";
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function CampaignPage() {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [premise, setPremise] = useState("");
  const [characterId, setCharacterId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextCampaigns, nextCharacters] = await Promise.all([
        api.campaigns(),
        api.characters(),
      ]);
      setCampaigns(nextCampaigns);
      setCharacters(nextCharacters);
      setCharacterId((current) =>
        current && nextCharacters.some((item) => item.id === current)
          ? current
          : (nextCharacters[0]?.id ?? ""),
      );
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    if (!characterId) {
      setFormError("Сначала создайте персонажа");
      return;
    }
    if (!name.trim()) {
      setFormError("Укажите название кампании");
      return;
    }
    setSubmitting(true);
    try {
      const created = await api.createCampaign({
        name: name.trim(),
        character_id: characterId,
        premise: premise.trim() || null,
      });
      setCampaigns((previous) => [created, ...previous]);
      setName("");
      setPremise("");
      navigate(`/campaigns/${created.id}`);
    } catch (submitError) {
      setFormError(errorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(campaignId: string) {
    if (!window.confirm("Удалить кампанию вместе с историей сообщений?")) {
      return;
    }
    try {
      await api.deleteCampaign(campaignId);
      setCampaigns((previous) =>
        previous.filter((campaign) => campaign.id !== campaignId),
      );
    } catch (deleteError) {
      setError(errorMessage(deleteError));
    }
  }

  if (loading) {
    return <p className="muted">Загружаем кампании...</p>;
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Шаг 2</p>
          <h2>Кампании</h2>
          <p className="muted">
            Одна кампания — один ваш персонаж. Мастер ведёт историю и помнит
            ключевые факты.
          </p>
        </div>
        <Link className="button ghost" to="/characters">
          К персонажам
        </Link>
      </header>

      {error && <p className="alert error">{error}</p>}

      <div className="two-column">
        <section className="card">
          <h3>Новая кампания</h3>
          {characters.length === 0 ? (
            <div className="empty">
              <p>Для кампании нужен персонаж.</p>
              <Link className="button primary" to="/characters">
                Создать персонажа
              </Link>
            </div>
          ) : (
            <form className="stack" onSubmit={handleSubmit}>
              <label className="field">
                <span>Название</span>
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={100}
                  placeholder="Например, Пропавшая шахта"
                  required
                />
              </label>

              <label className="field">
                <span>Персонаж</span>
                <select
                  value={characterId}
                  onChange={(event) => setCharacterId(event.target.value)}
                >
                  {characters.map((character) => (
                    <option key={character.id} value={character.id}>
                      {character.name} · {character.character_class}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Пожелание к кампании (необязательно)</span>
                <textarea
                  value={premise}
                  onChange={(event) => setPremise(event.target.value)}
                  maxLength={500}
                  rows={3}
                  placeholder="Жанр, тон или сеттинг: например, мрачное городское фэнтези"
                />
              </label>

              {formError && <p className="alert error">{formError}</p>}

              <button
                className="button primary"
                type="submit"
                disabled={submitting}
              >
                {submitting ? "Создаём..." : "Начать кампанию"}
              </button>
            </form>
          )}
        </section>

        <section className="card">
          <h3>Мои кампании</h3>
          {campaigns.length === 0 ? (
            <p className="muted">
              Пока нет кампаний. Создайте первую и отправьте действие мастеру.
            </p>
          ) : (
            <div className="stack">
              {campaigns.map((campaign) => {
                const character = characters.find(
                  (item) => item.id === campaign.character_id,
                );
                return (
                  <article key={campaign.id} className="campaign-card">
                    <div>
                      <h4>{campaign.name}</h4>
                      <p className="muted small">
                        {character
                          ? `${character.name} · ${character.character_class}`
                          : "Персонаж удалён"}{" "}
                        · {formatDate(campaign.created_at)}
                      </p>
                      <p className="muted small">
                        Фактов в памяти: {campaign.summary.facts.length}, целей:{" "}
                        {campaign.summary.goals.length}
                      </p>
                      {campaign.premise && (
                        <p className="muted small">{campaign.premise}</p>
                      )}
                    </div>
                    <div className="button-row">
                      <Link
                        className="button primary"
                        to={`/campaigns/${campaign.id}`}
                      >
                        Открыть
                      </Link>
                      <button
                        className="button ghost danger"
                        type="button"
                        onClick={() => void handleDelete(campaign.id)}
                      >
                        Удалить
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
