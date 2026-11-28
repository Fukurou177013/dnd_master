import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "./api";
import { CharacterForm, draftFromCharacter, emptyDraft } from "./CharacterForm";
import type {
  AbilityKey,
  Character,
  CharacterCreatePayload,
  CharacterOptions,
  CharacterUpdatePayload,
} from "./types";

function signed(value: number): string {
  return value >= 0 ? `+${value}` : `${value}`;
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Не удалось выполнить запрос";
}

const ABILITIES: AbilityKey[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

export function CharacterPage() {
  const [options, setOptions] = useState<CharacterOptions | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createKey, setCreateKey] = useState(0);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextOptions, nextCharacters] = await Promise.all([
        api.characterOptions(),
        api.characters(),
      ]);
      setOptions(nextOptions);
      setCharacters(nextCharacters);
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreate(payload: CharacterCreatePayload) {
    setCreating(true);
    setCreateError(null);
    try {
      const created = await api.createCharacter(payload);
      setCharacters((previous) => [created, ...previous]);
      setCreateKey((previous) => previous + 1);
    } catch (createFailure) {
      setCreateError(errorMessage(createFailure));
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdate(
    characterId: string,
    payload: CharacterUpdatePayload,
  ) {
    setSavingEdit(true);
    setEditError(null);
    try {
      const updated = await api.updateCharacter(characterId, payload);
      setCharacters((previous) =>
        previous.map((character) =>
          character.id === characterId ? updated : character,
        ),
      );
      setEditingId(null);
    } catch (updateFailure) {
      setEditError(errorMessage(updateFailure));
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleAdjustHp(character: Character, delta: number) {
    const next = Math.min(
      character.max_hp,
      Math.max(0, character.current_hp + delta),
    );
    if (next === character.current_hp) {
      return;
    }
    try {
      const updated = await api.updateCharacter(character.id, {
        current_hp: next,
      });
      setCharacters((previous) =>
        previous.map((item) => (item.id === character.id ? updated : item)),
      );
    } catch (hpFailure) {
      setError(errorMessage(hpFailure));
    }
  }

  async function handleDelete(characterId: string) {
    if (!window.confirm("Удалить персонажа и связанные кампании?")) {
      return;
    }
    try {
      await api.deleteCharacter(characterId);
      setCharacters((previous) =>
        previous.filter((character) => character.id !== characterId),
      );
    } catch (deleteError) {
      setError(errorMessage(deleteError));
    }
  }

  if (loading) {
    return <p className="muted">Загружаем лист персонажа...</p>;
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Шаг 1</p>
          <h2>Персонаж</h2>
          <p className="muted">
            Выберите стартовые опции SRD. Хиты, класс брони, скорость и навыки
            рассчитывает сервер.
          </p>
        </div>
      </header>

      {error && <p className="alert error">{error}</p>}

      <div className="two-column">
        <section className="card">
          <h3>Новый персонаж</h3>
          {!options ? (
            <p className="muted">Не удалось загрузить каталог опций.</p>
          ) : (
            <CharacterForm
              key={createKey}
              options={options}
              initial={emptyDraft(options)}
              submitLabel="Создать персонажа"
              pendingLabel="Создаём..."
              submitting={creating}
              error={createError}
              onSubmit={(payload) => void handleCreate(payload)}
            />
          )}
        </section>

        <section className="stack">
          <div className="card">
            <h3>Мои персонажи</h3>
            {characters.length === 0 ? (
              <p className="muted">
                Пока нет персонажей. Заполните форму слева, чтобы начать.
              </p>
            ) : (
              <div className="stack">
                {characters.map((character) => {
                  if (options && editingId === character.id) {
                    return (
                      <article key={character.id} className="sheet">
                        <header className="sheet-header">
                          <div>
                            <h4>Редактирование листа</h4>
                            <p className="muted small">{character.name}</p>
                          </div>
                        </header>
                        <CharacterForm
                          options={options}
                          initial={draftFromCharacter(character)}
                          submitLabel="Сохранить изменения"
                          pendingLabel="Сохраняем..."
                          submitting={savingEdit}
                          error={editError}
                          onSubmit={(payload) =>
                            void handleUpdate(character.id, payload)
                          }
                          onCancel={() => {
                            setEditingId(null);
                            setEditError(null);
                          }}
                        />
                      </article>
                    );
                  }
                  return (
                    <CharacterSheet
                      key={character.id}
                      character={character}
                      onEdit={() => {
                        setEditingId(character.id);
                        setEditError(null);
                      }}
                      onDelete={() => void handleDelete(character.id)}
                      onAdjustHp={(delta) => handleAdjustHp(character, delta)}
                    />
                  );
                })}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function CharacterSheet({
  character,
  onEdit,
  onDelete,
  onAdjustHp,
}: {
  character: Character;
  onEdit: () => void;
  onDelete: () => void;
  onAdjustHp: (delta: number) => Promise<void>;
}) {
  const [hpPending, setHpPending] = useState(false);

  const modifiers = character.data.ability_modifiers;
  const skills = character.data.skill_proficiencies ?? [];
  const skillModifiers = character.data.skill_modifiers ?? {};
  const savingThrows = character.data.saving_throws;

  async function adjustHp(delta: number) {
    setHpPending(true);
    try {
      await onAdjustHp(delta);
    } finally {
      setHpPending(false);
    }
  }

  return (
    <article className="sheet">
      <header className="sheet-header">
        <div>
          <h4>{character.name}</h4>
          <p className="muted small">
            {character.species} · {character.character_class} ·{" "}
            {character.background} · уровень {character.level}
          </p>
        </div>
        <div className="sheet-actions">
          <button className="button ghost" type="button" onClick={onEdit}>
            Редактировать
          </button>
          <button
            className="button ghost danger"
            type="button"
            onClick={onDelete}
          >
            Удалить
          </button>
        </div>
      </header>

      <div className="stat-row">
        <div className="stat">
          <span className="stat-label">HP</span>
          <strong>
            {character.current_hp}/{character.max_hp}
          </strong>
          <div className="hp-controls">
            <button
              className="button ghost"
              type="button"
              aria-label="Урон"
              disabled={hpPending || character.current_hp <= 0}
              onClick={() => void adjustHp(-1)}
            >
              −
            </button>
            <button
              className="button ghost"
              type="button"
              aria-label="Лечение"
              disabled={hpPending || character.current_hp >= character.max_hp}
              onClick={() => void adjustHp(1)}
            >
              +
            </button>
          </div>
        </div>
        <div className="stat">
          <span className="stat-label">КБ</span>
          <strong>{character.armor_class}</strong>
        </div>
        <div className="stat">
          <span className="stat-label">Скорость</span>
          <strong>{character.speed} фт</strong>
        </div>
        <div className="stat">
          <span className="stat-label">Тёмное зрение</span>
          <strong>
            {character.data.darkvision
              ? `${character.data.darkvision} фт`
              : "—"}
          </strong>
        </div>
        <div className="stat">
          <span className="stat-label">Инициатива</span>
          <strong>{signed(character.data.initiative ?? 0)}</strong>
        </div>
        <div className="stat">
          <span className="stat-label">Бонус владения</span>
          <strong>{signed(character.data.proficiency_bonus ?? 2)}</strong>
        </div>
        <div className="stat">
          <span className="stat-label">Пасс. внимательность</span>
          <strong>{character.data.passive_perception ?? 10}</strong>
        </div>
      </div>

      <div className="ability-grid">
        {ABILITIES.map((ability) => (
          <div key={ability} className="ability">
            <span>{ability.slice(0, 3).toUpperCase()}</span>
            <strong>{character[ability]}</strong>
            <small>
              {signed(
                modifiers?.[ability] ??
                  Math.floor((character[ability] - 10) / 2),
              )}
            </small>
          </div>
        ))}
      </div>

      <div>
        <p className="stat-label">Спасброски</p>
        <div className="tag-row">
          {ABILITIES.map((ability) => (
            <span key={ability} className="tag">
              {ability.slice(0, 3).toUpperCase()}{" "}
              {savingThrows ? signed(savingThrows[ability] ?? 0) : "—"}
            </span>
          ))}
        </div>
      </div>

      <div>
        <p className="stat-label">Навыки с владением</p>
        <div className="tag-row">
          {skills.length === 0 ? (
            <span className="muted small">Нет выбранных навыков</span>
          ) : (
            skills.map((skill) => (
              <span key={skill} className="tag">
                {skill} {signed(skillModifiers[skill] ?? 0)}
              </span>
            ))
          )}
        </div>
      </div>

      {character.notes && <p className="notes">{character.notes}</p>}
    </article>
  );
}
