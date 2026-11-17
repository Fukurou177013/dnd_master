import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Link, useParams } from "react-router-dom";

import { api, ApiError } from "./api";
import type {
  AbilityKey,
  Campaign,
  CampaignMessage,
  Character,
  CharacterOptions,
  CheckRequest,
  MessageRequest,
  Roll,
} from "./types";

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Не удалось выполнить запрос";
}

function signed(value: number): string {
  return value >= 0 ? `+${value}` : `${value}`;
}

function mergeMessages(
  current: CampaignMessage[],
  incoming: CampaignMessage[],
): CampaignMessage[] {
  const byId = new Map(current.map((message) => [message.id, message]));
  for (const message of incoming) {
    byId.set(message.id, message);
  }
  return [...byId.values()].sort((left, right) => left.sequence - right.sequence);
}

export function CampaignChatPage() {
  const { campaignId = "" } = useParams();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [character, setCharacter] = useState<Character | null>(null);
  const [options, setOptions] = useState<CharacterOptions | null>(null);
  const [messages, setMessages] = useState<CampaignMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [content, setContent] = useState("");
  const [checkEnabled, setCheckEnabled] = useState(false);
  const [ability, setAbility] = useState<AbilityKey>("wisdom");
  const [skill, setSkill] = useState("");
  const [dc, setDc] = useState(15);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [lastAttempt, setLastAttempt] = useState<MessageRequest | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const load = useCallback(async () => {
    if (!campaignId) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [nextCampaign, nextMessages, nextOptions, characters] =
        await Promise.all([
          api.campaign(campaignId),
          api.messages(campaignId),
          api.characterOptions(),
          api.characters(),
        ]);
      setCampaign(nextCampaign);
      setMessages(nextMessages);
      setOptions(nextOptions);
      setCharacter(
        characters.find((item) => item.id === nextCampaign.character_id) ??
          null,
      );
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  const skillOptions =
    options?.skills.filter((item) => item.ability === ability) ?? [];
  const maxMessageLength = options?.limits.max_message_length;

  function handleAbilityChange(nextAbility: AbilityKey) {
    setAbility(nextAbility);
    const currentSkill = options?.skills.find((item) => item.name === skill);
    if (currentSkill && currentSkill.ability !== nextAbility) {
      setSkill("");
    }
  }

  async function send(request: MessageRequest) {
    setSending(true);
    setSendError(null);
    try {
      const exchange = await api.sendMessage(campaignId, request);
      setMessages((previous) =>
        mergeMessages(previous, [
          exchange.user_message,
          exchange.assistant_message,
        ]),
      );
      setCampaign(await api.campaign(campaignId));
      setContent("");
      setLastAttempt(null);
    } catch (sendFailure) {
      const retryable =
        !(sendFailure instanceof ApiError) || sendFailure.status >= 500;
      setLastAttempt(retryable ? request : null);
      setSendError(errorMessage(sendFailure));
      if (
        sendFailure instanceof ApiError &&
        (sendFailure.status === 503 || sendFailure.status === 504)
      ) {
        try {
          setMessages(await api.messages(campaignId));
        } catch {
          setSendError(
            "Сообщение сохранено, но историю не удалось перезагрузить.",
          );
        }
      }
    } finally {
      setSending(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = content.trim();
    if (!text || sending) {
      return;
    }
    const check: CheckRequest | null = checkEnabled
      ? { ability, skill: skill || null, dc }
      : null;
    await send({
      content: text,
      client_message_id: crypto.randomUUID(),
      check,
    });
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  if (loading) {
    return <p className="muted">Открываем кампанию...</p>;
  }

  if (!campaign) {
    return (
      <div className="page">
        <p className="alert error">{error ?? "Кампания не найдена"}</p>
        <Link className="button ghost" to="/campaigns">
          Вернуться к кампаниям
        </Link>
      </div>
    );
  }

  return (
    <div className="page chat-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Кампания</p>
          <h2>{campaign.name}</h2>
          <p className="muted">
            {character
              ? `${character.name} · ${character.species} · ${character.character_class} · ${character.current_hp}/${character.max_hp} HP`
              : "Персонаж не найден"}
          </p>
        </div>
        <Link className="button ghost" to="/campaigns">
          К кампаниям
        </Link>
      </header>

      {error && <p className="alert error">{error}</p>}

      <div className="chat-layout">
        <section className="card chat-card">
          <div className="messages" aria-live="polite">
            {messages.length === 0 && (
              <div className="empty chat-empty">
                <p>Мастер ждёт вашего действия.</p>
                <p className="muted small">
                  Опишите, что делает персонаж. Для проверки включите её ниже:
                  сервер сам бросит d20 и применит модификатор.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <article
                key={message.id}
                className={`message ${message.role}`}
              >
                <div className="message-role">
                  {message.role === "user" ? "Вы" : "Мастер"}
                </div>
                <p className="message-text">{message.content}</p>
                {message.roll && <RollCard roll={message.roll} />}
                {message.sources.length > 0 && (
                  <details className="sources">
                    <summary>
                      Источники SRD ({message.sources.length})
                    </summary>
                    <ul>
                      {message.sources.map((source) => (
                        <li key={source.id}>
                          <strong>{source.title}</strong>
                          <p className="muted small">
                            {source.section} · {source.source} ·{" "}
                            {source.license}
                          </p>
                          <p className="small">{source.excerpt}</p>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </article>
            ))}
            <div ref={endRef} />
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <textarea
              value={content}
              onChange={(event) => setContent(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              maxLength={maxMessageLength}
              rows={3}
              placeholder="Что делает ваш персонаж?"
              disabled={sending || maxMessageLength === undefined}
              required
            />

            <div className="composer-controls">
              <label className="check inline">
                <input
                  type="checkbox"
                  checked={checkEnabled}
                  onChange={(event) => setCheckEnabled(event.target.checked)}
                  disabled={sending}
                />
                <span>Проверка</span>
              </label>

              {checkEnabled && (
                <div className="check-controls">
                  <select
                    value={ability}
                    onChange={(event) =>
                      handleAbilityChange(event.target.value as AbilityKey)
                    }
                    disabled={sending}
                    aria-label="Характеристика"
                  >
                    {options?.abilities.map((item) => (
                      <option key={item.key} value={item.key}>
                        {item.label}
                      </option>
                    ))}
                  </select>

                  <select
                    value={skill}
                    onChange={(event) => setSkill(event.target.value)}
                    disabled={sending}
                    aria-label="Навык"
                  >
                    <option value="">Без навыка</option>
                    {skillOptions.map((item) => (
                      <option key={item.name} value={item.name}>
                        {item.name}
                      </option>
                    ))}
                  </select>

                  <label className="dc-field">
                    <span>DC</span>
                    <input
                      type="number"
                      min={5}
                      max={30}
                      value={dc}
                      onChange={(event) => setDc(Number(event.target.value))}
                      disabled={sending}
                    />
                  </label>
                </div>
              )}

              <button
                className="button primary"
                type="submit"
                disabled={sending || !content.trim()}
              >
                {sending ? "Мастер думает..." : "Отправить"}
              </button>
            </div>

            {sendError && (
              <div className="alert error send-error">
                <span>{sendError}</span>
                {lastAttempt && (
                  <button
                    className="button ghost"
                    type="button"
                    onClick={() => void send(lastAttempt)}
                    disabled={sending}
                  >
                    Повторить
                  </button>
                )}
              </div>
            )}
          </form>
        </section>

        <aside className="card memory-card">
          <h3>Память кампании</h3>
          <p className="muted small">
            Резюме обновляется после каждого ответа и не заменяет историю.
          </p>
          <MemorySection title="Факты" values={campaign.summary.facts} />
          <MemorySection title="Цели" values={campaign.summary.goals} />
          <MemorySection title="NPC" values={campaign.summary.npcs} />
          <MemorySection
            title="Локации"
            values={campaign.summary.locations}
          />
          <MemorySection
            title="Незавершённые события"
            values={campaign.summary.open_threads}
          />
        </aside>
      </div>
    </div>
  );
}

function RollCard({ roll }: { roll: Roll }) {
  return (
    <div
      className={`roll-card ${roll.success ? "success" : "failure"}`}
      title="Бросок рассчитан сервером"
    >
      <strong>
        {roll.ability_label}
        {roll.skill ? ` · ${roll.skill}` : ""}
      </strong>
      <span>
        d20 {roll.d20} {signed(roll.modifier)} = {roll.total} против DC{" "}
        {roll.dc}
      </span>
      <span className="roll-outcome">
        {roll.success ? "Успех" : "Провал"}
        {roll.proficient ? " · владение" : ""}
      </span>
    </div>
  );
}

function MemorySection({
  title,
  values,
}: {
  title: string;
  values: string[];
}) {
  return (
    <section className="memory-section">
      <h4>{title}</h4>
      {values.length === 0 ? (
        <p className="muted small">Пока пусто</p>
      ) : (
        <ul>
          {values.map((value, index) => (
            <li key={`${value}-${index}`}>{value}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
