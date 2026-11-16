import { useCallback, useEffect, useState, type FormEvent } from "react";

import { api, ApiError } from "./api";
import type {
  AbilityKey,
  Character,
  CharacterCreatePayload,
  CharacterOptions,
} from "./types";

type Stats = Record<AbilityKey, number>;

const DEFAULT_STATS: Stats = {
  strength: 8,
  dexterity: 14,
  constitution: 12,
  intelligence: 16,
  wisdom: 10,
  charisma: 10,
};

function signed(value: number): string {
  return value >= 0 ? `+${value}` : `${value}`;
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Не удалось выполнить запрос";
}

export function CharacterPage() {
  const [options, setOptions] = useState<CharacterOptions | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [species, setSpecies] = useState("Elf");
  const [characterClass, setCharacterClass] = useState("Wizard");
  const [background, setBackground] = useState("Sage");
  const [stats, setStats] = useState<Stats>(DEFAULT_STATS);
  const [notes, setNotes] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

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

  useEffect(() => {
    if (!options) {
      return;
    }
    const currentBackground =
      options.backgrounds.find((item) => item.name === background) ??
      options.backgrounds[0];
    if (currentBackground) {
      setSelectedSkills(currentBackground.skills);
    }
  }, [options, background]);

  const classOption = options?.classes.find(
    (item) => item.name === characterClass,
  );
  const backgroundOption = options?.backgrounds.find(
    (item) => item.name === background,
  );
  const backgroundSkills = new Set(backgroundOption?.skills ?? []);
  const classChoices = new Set(classOption?.skill_choices ?? []);
  const availableSkills =
    options?.skills.filter(
      (skill) =>
        backgroundSkills.has(skill.name) || classChoices.has(skill.name),
    ) ?? [];
  const classSkillCount = selectedSkills.filter(
    (skill) => classChoices.has(skill) && !backgroundSkills.has(skill),
  ).length;
  const maxClassSkills = classOption?.skill_count ?? 2;

  function handleBackgroundChange(nextBackground: string) {
    setBackground(nextBackground);
    setSelectedSkills([]);
  }

  function handleClassChange(nextClass: string) {
    setCharacterClass(nextClass);
    const nextClassOption = options?.classes.find(
      (item) => item.name === nextClass,
    );
    const allowed = new Set(nextClassOption?.skill_choices ?? []);
    const maxSkills = nextClassOption?.skill_count ?? 2;
    setSelectedSkills((previous) => {
      const retainedBackgroundSkills = previous.filter((skill) =>
        backgroundSkills.has(skill),
      );
      const retainedClassSkills = previous
        .filter(
          (skill) => !backgroundSkills.has(skill) && allowed.has(skill),
        )
        .slice(0, maxSkills);
      return [...retainedBackgroundSkills, ...retainedClassSkills];
    });
  }

  function toggleSkill(skill: string) {
    if (backgroundSkills.has(skill)) {
      return;
    }
    setSelectedSkills((previous) => {
      if (previous.includes(skill)) {
        return previous.filter((item) => item !== skill);
      }
      const currentClassCount = previous.filter(
        (item) => classChoices.has(item) && !backgroundSkills.has(item),
      ).length;
      if (currentClassCount >= maxClassSkills) {
        return previous;
      }
      return [...previous, skill];
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError("Укажите имя персонажа");
      return;
    }
    for (const [, score] of Object.entries(stats)) {
      if (!Number.isInteger(score) || score < 3 || score > 18) {
        setFormError("Характеристики должны быть целыми числами от 3 до 18");
        return;
      }
    }

    const payload: CharacterCreatePayload = {
      name: name.trim(),
      level: 1,
      species,
      character_class: characterClass,
      background,
      ...stats,
      notes: notes.trim() ? notes.trim() : null,
      data: { skill_proficiencies: selectedSkills },
    };

    setSubmitting(true);
    try {
      const created = await api.createCharacter(payload);
      setCharacters((previous) => [created, ...previous]);
      setName("");
      setNotes("");
    } catch (submitError) {
      setFormError(errorMessage(submitError));
    } finally {
      setSubmitting(false);
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
            <form className="stack" onSubmit={handleSubmit}>
              <label className="field">
                <span>Имя</span>
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={100}
                  placeholder="Например, Ариэль"
                  required
                />
              </label>

              <div className="form-grid">
                <label className="field">
                  <span>Вид</span>
                  <select
                    value={species}
                    onChange={(event) => setSpecies(event.target.value)}
                  >
                    {options.species.map((item) => (
                      <option key={item.name} value={item.name}>
                        {item.name} (скорость {item.speed})
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>Класс</span>
                  <select
                    value={characterClass}
                    onChange={(event) => handleClassChange(event.target.value)}
                  >
                    {options.classes.map((item) => (
                      <option key={item.name} value={item.name}>
                        {item.name} (d{item.hit_die})
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>Предыстория</span>
                  <select
                    value={background}
                    onChange={(event) =>
                      handleBackgroundChange(event.target.value)
                    }
                  >
                    {options.backgrounds.map((item) => (
                      <option key={item.name} value={item.name}>
                        {item.name}: {item.skills.join(", ")}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <fieldset className="fieldset">
                <legend>Характеристики</legend>
                <div className="ability-inputs">
                  {options.abilities.map((ability) => (
                    <label key={ability.key} className="field compact-field">
                      <span>{ability.label}</span>
                      <input
                        type="number"
                        min={3}
                        max={18}
                        value={stats[ability.key]}
                        onChange={(event) =>
                          setStats((previous) => ({
                            ...previous,
                            [ability.key]: Number(event.target.value),
                          }))
                        }
                      />
                    </label>
                  ))}
                </div>
              </fieldset>

              <fieldset className="fieldset">
                <legend>
                  Навыки
                  <span className="muted small">
                    {" "}
                    классовых: {classSkillCount}/{maxClassSkills}
                  </span>
                </legend>
                <div className="skill-grid">
                  {availableSkills.map((skill) => {
                    const isBackground = backgroundSkills.has(skill.name);
                    const checked = selectedSkills.includes(skill.name);
                    const disabled =
                      isBackground ||
                      (!checked && classSkillCount >= maxClassSkills);
                    return (
                      <label
                        key={skill.name}
                        className={
                          isBackground ? "check background" : "check"
                        }
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={disabled}
                          onChange={() => toggleSkill(skill.name)}
                        />
                        <span>{skill.name}</span>
                        <small className="muted">
                          {isBackground ? "предыстория" : skill.ability}
                        </small>
                      </label>
                    );
                  })}
                </div>
              </fieldset>

              <label className="field">
                <span>Заметки</span>
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  maxLength={10000}
                  rows={3}
                  placeholder="Внешность, характер, цели"
                />
              </label>

              {formError && <p className="alert error">{formError}</p>}

              <button
                className="button primary"
                type="submit"
                disabled={submitting}
              >
                {submitting ? "Создаём..." : "Создать персонажа"}
              </button>
            </form>
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
                {characters.map((character) => (
                  <CharacterSheet
                    key={character.id}
                    character={character}
                    onDelete={() => void handleDelete(character.id)}
                  />
                ))}
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
  onDelete,
}: {
  character: Character;
  onDelete: () => void;
}) {
  const abilities: AbilityKey[] = [
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
  ];
  const modifiers = character.data.ability_modifiers;
  const skills = character.data.skill_proficiencies ?? [];
  const skillModifiers = character.data.skill_modifiers ?? {};

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
        <button className="button ghost danger" type="button" onClick={onDelete}>
          Удалить
        </button>
      </header>

      <div className="stat-row">
        <div className="stat">
          <span className="stat-label">HP</span>
          <strong>
            {character.current_hp}/{character.max_hp}
          </strong>
        </div>
        <div className="stat">
          <span className="stat-label">КБ</span>
          <strong>{character.armor_class}</strong>
        </div>
        <div className="stat">
          <span className="stat-label">Скорость</span>
          <strong>{character.speed}</strong>
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
        {abilities.map((ability) => (
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
