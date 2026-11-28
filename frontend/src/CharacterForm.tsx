import { useEffect, useRef, useState, type FormEvent } from "react";

import { api, ApiError } from "./api";
import type {
  AbilityKey,
  AbilityScoreMethod,
  BackgroundBonusMode,
  Character,
  CharacterCreatePayload,
  CharacterOptions,
  SpeciesOption,
} from "./types";

const ABILITIES: AbilityKey[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

const FALLBACK_STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];

type Stats = Record<AbilityKey, number>;

const DEFAULT_STATS: Stats = {
  strength: 8,
  dexterity: 8,
  constitution: 8,
  intelligence: 8,
  wisdom: 8,
  charisma: 8,
};

export interface BackgroundBonusSelection {
  mode: BackgroundBonusMode;
  plus_two: AbilityKey | null;
  plus_one: AbilityKey | null;
}

export interface CharacterDraft {
  name: string;
  level: number;
  species: string;
  character_class: string;
  background: string;
  ability_score_method: AbilityScoreMethod | null;
  background_bonus: BackgroundBonusSelection;
  stats: Stats;
  notes: string;
  skills: string[];
}

function bonusSelectionFromCharacter(
  character: Character,
): BackgroundBonusSelection {
  const allocation = character.data.background_ability_bonus ?? {};
  const positive = ABILITIES.filter((ability) => (allocation[ability] ?? 0) > 0);
  if (
    positive.length === 3 &&
    positive.every((ability) => allocation[ability] === 1)
  ) {
    return { mode: "one_one_one", plus_two: null, plus_one: null };
  }
  const plusTwo = positive.find((ability) => allocation[ability] === 2);
  const plusOne = positive.find((ability) => allocation[ability] === 1);
  if (plusTwo && plusOne) {
    return { mode: "two_one", plus_two: plusTwo, plus_one: plusOne };
  }
  return { mode: "two_one", plus_two: null, plus_one: null };
}

export function draftFromCharacter(character: Character): CharacterDraft {
  const legacySkills = Array.isArray(character.data.skills)
    ? (character.data.skills as string[])
    : [];
  const bonus = character.data.background_ability_bonus ?? {};
  return {
    name: character.name,
    level: character.level,
    species: character.species,
    character_class: character.character_class,
    background: character.background,
    ability_score_method: character.data.ability_score_method ?? "manual",
    background_bonus: bonusSelectionFromCharacter(character),
    stats: {
      strength: character.strength - (bonus.strength ?? 0),
      dexterity: character.dexterity - (bonus.dexterity ?? 0),
      constitution: character.constitution - (bonus.constitution ?? 0),
      intelligence: character.intelligence - (bonus.intelligence ?? 0),
      wisdom: character.wisdom - (bonus.wisdom ?? 0),
      charisma: character.charisma - (bonus.charisma ?? 0),
    },
    notes: character.notes ?? "",
    skills: [...(character.data.skill_proficiencies ?? legacySkills)],
  };
}

export function emptyDraft(options: CharacterOptions): CharacterDraft {
  const background = options.backgrounds[0];
  return {
    name: "",
    level: options.level.min,
    species: options.species[0]?.name ?? "",
    character_class: options.classes[0]?.name ?? "",
    background: background?.name ?? "",
    ability_score_method: null,
    background_bonus: { mode: "two_one", plus_two: null, plus_one: null },
    stats: { ...DEFAULT_STATS },
    notes: "",
    skills: background ? [...background.skills] : [],
  };
}

function standardArrayValues(options: CharacterOptions): number[] {
  const method = options.ability_generation.methods.find(
    (item) => item.key === "standard_array",
  );
  return [...(method?.values ?? FALLBACK_STANDARD_ARRAY)].sort(
    (left, right) => right - left,
  );
}

function picksFromStats(
  stats: Stats,
  values: number[],
): Partial<Record<AbilityKey, number>> {
  const remaining = [...values];
  const picks: Partial<Record<AbilityKey, number>> = {};
  for (const ability of ABILITIES) {
    const index = remaining.indexOf(stats[ability]);
    if (index !== -1) {
      picks[ability] = stats[ability];
      remaining.splice(index, 1);
    }
  }
  return picks;
}

function standardPickedStats(
  picks: Partial<Record<AbilityKey, number>>,
): Stats {
  const stats = { ...DEFAULT_STATS };
  for (const ability of ABILITIES) {
    stats[ability] = picks[ability] ?? stats[ability];
  }
  return stats;
}

function clampStats(stats: Stats, min: number, max: number): Stats {
  const next = { ...stats };
  for (const ability of ABILITIES) {
    const score = Number.isFinite(next[ability]) ? next[ability] : min;
    next[ability] = Math.min(max, Math.max(min, Math.round(score)));
  }
  return next;
}

function sortedKey(values: number[]): string {
  return [...values].sort((left, right) => left - right).join(",");
}

function speciesOptionLabel(item: SpeciesOption): string {
  const darkvision = item.darkvision
    ? `, тёмное зрение ${item.darkvision} фт`
    : "";
  return `${item.name} (скорость ${item.speed} фт${darkvision})`;
}

interface CharacterFormProps {
  options: CharacterOptions;
  initial: CharacterDraft;
  submitLabel: string;
  pendingLabel: string;
  submitting: boolean;
  error: string | null;
  onSubmit: (payload: CharacterCreatePayload) => void;
  onCancel?: () => void;
}

export function CharacterForm({
  options,
  initial,
  submitLabel,
  pendingLabel,
  submitting,
  error,
  onSubmit,
  onCancel,
}: CharacterFormProps) {
  const standardValues = standardArrayValues(options);
  const [name, setName] = useState(initial.name);
  const [level, setLevel] = useState(initial.level);
  const [species, setSpecies] = useState(initial.species);
  const [characterClass, setCharacterClass] = useState(initial.character_class);
  const [background, setBackground] = useState(initial.background);
  const [method, setMethod] = useState<AbilityScoreMethod | null>(
    initial.ability_score_method,
  );
  const [stats, setStats] = useState<Stats>(initial.stats);
  const [standardPicks, setStandardPicks] = useState<
    Partial<Record<AbilityKey, number>>
  >(() =>
    initial.ability_score_method === "standard_array"
      ? picksFromStats(initial.stats, standardValues)
      : {},
  );
  const [pointsFlash, setPointsFlash] = useState(false);
  const pointsFlashTimer = useRef<number | null>(null);
  const [rolled, setRolled] = useState(
    initial.ability_score_method === "roll_4d6",
  );
  const [rolling, setRolling] = useState(false);
  const [bonusMode, setBonusMode] = useState<BackgroundBonusMode>(
    initial.background_bonus.mode,
  );
  const [bonusPlusTwo, setBonusPlusTwo] = useState<AbilityKey | null>(
    initial.background_bonus.plus_two,
  );
  const [bonusPlusOne, setBonusPlusOne] = useState<AbilityKey | null>(
    initial.background_bonus.plus_one,
  );
  const [notes, setNotes] = useState(initial.notes);
  const [selectedSkills, setSelectedSkills] = useState<string[]>(initial.skills);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (pointsFlashTimer.current !== null) {
        window.clearTimeout(pointsFlashTimer.current);
      }
    };
  }, []);

  const classOption = options.classes.find(
    (item) => item.name === characterClass,
  );
  const backgroundOption = options.backgrounds.find(
    (item) => item.name === background,
  );
  const backgroundSkills = new Set(backgroundOption?.skills ?? []);
  const backgroundAbilityScores = backgroundOption?.ability_scores ?? [];
  const bonusModes = options.background_ability_bonus.modes;
  const classChoices = new Set(classOption?.skill_choices ?? []);
  const availableSkills = options.skills.filter(
    (skill) =>
      backgroundSkills.has(skill.name) || classChoices.has(skill.name),
  );
  const classSkillCount = selectedSkills.filter(
    (skill) => classChoices.has(skill) && !backgroundSkills.has(skill),
  ).length;
  const maxClassSkills = classOption?.skill_count ?? 2;

  const standardPickedCount = ABILITIES.filter(
    (ability) => standardPicks[ability] !== undefined,
  ).length;
  const currentStandardValue = standardValues[standardPickedCount] ?? null;
  const unassignedStandardAbilities = ABILITIES.filter(
    (ability) => standardPicks[ability] === undefined,
  );
  const pointBuyMethod = options.ability_generation.methods.find(
    (item) => item.key === "point_buy",
  );
  const pointBuyBudget = pointBuyMethod?.budget ?? 27;
  const pointBuyMin = pointBuyMethod?.min ?? 8;
  const pointBuyMax = pointBuyMethod?.max ?? 15;
  const pointBuyCosts = pointBuyMethod?.costs ?? {};
  const rollMethod = options.ability_generation.methods.find(
    (item) => item.key === "roll_4d6",
  );
  const rollDice = rollMethod?.dice ?? {
    count: 4,
    sides: 6,
    drop_lowest: 1,
  };
  const pointBuySpent = ABILITIES.reduce(
    (total, ability) => total + (pointBuyCosts[String(stats[ability])] ?? 0),
    0,
  );
  const pointBuyLeft = pointBuyBudget - pointBuySpent;

  function abilityLabel(key: AbilityKey): string {
    return options.abilities.find((item) => item.key === key)?.label ?? key;
  }

  function bonusAllocation(): Partial<Record<AbilityKey, number>> | null {
    if (backgroundAbilityScores.length !== 3) {
      return null;
    }
    if (bonusMode === "one_one_one") {
      return Object.fromEntries(
        backgroundAbilityScores.map((ability) => [ability, 1]),
      ) as Partial<Record<AbilityKey, number>>;
    }
    if (
      !bonusPlusTwo ||
      !bonusPlusOne ||
      bonusPlusTwo === bonusPlusOne ||
      !backgroundAbilityScores.includes(bonusPlusTwo) ||
      !backgroundAbilityScores.includes(bonusPlusOne)
    ) {
      return null;
    }
    return { [bonusPlusTwo]: 2, [bonusPlusOne]: 1 };
  }

  function validateBackgroundBonus(): string | null {
    if (!bonusAllocation()) {
      return "Выберите бонусы характеристик от предыстории (+2/+1 или +1/+1/+1)";
    }
    return null;
  }

  function statsWithBonus(
    allocation: Partial<Record<AbilityKey, number>> | null,
    source: Stats = stats,
  ): Stats {
    const next = { ...source };
    if (allocation) {
      for (const ability of ABILITIES) {
        next[ability] += allocation[ability] ?? 0;
      }
    }
    return next;
  }

  function flashPoints() {
    if (pointsFlashTimer.current !== null) {
      window.clearTimeout(pointsFlashTimer.current);
    }
    setPointsFlash(true);
    pointsFlashTimer.current = window.setTimeout(() => {
      setPointsFlash(false);
      pointsFlashTimer.current = null;
    }, 800);
  }

  function handlePointBuyChange(ability: AbilityKey, nextValue: number) {
    const clamped = Math.min(
      pointBuyMax,
      Math.max(pointBuyMin, Math.round(nextValue)),
    );
    if (clamped === stats[ability]) {
      return;
    }
    const nextSpent =
      pointBuySpent -
      (pointBuyCosts[String(stats[ability])] ?? 0) +
      (pointBuyCosts[String(clamped)] ?? 0);
    if (nextSpent > pointBuyBudget) {
      flashPoints();
      return;
    }
    setScore(ability, clamped);
  }

  function assignStandardValue(ability: AbilityKey) {
    if (currentStandardValue === null) {
      return;
    }
    setStandardPicks((previous) => ({
      ...previous,
      [ability]: currentStandardValue,
    }));
    setScore(ability, currentStandardValue);
  }

  function resetStandardArray() {
    setStandardPicks({});
    setStats({ ...DEFAULT_STATS });
  }

  function handleBackgroundChange(nextBackground: string) {
    setBackground(nextBackground);
    const nextOption = options.backgrounds.find(
      (item) => item.name === nextBackground,
    );
    setSelectedSkills(nextOption ? [...nextOption.skills] : []);
    const nextAbilities = nextOption?.ability_scores ?? [];
    setBonusPlusTwo((previous) =>
      previous && nextAbilities.includes(previous) ? previous : null,
    );
    setBonusPlusOne((previous) =>
      previous && nextAbilities.includes(previous) ? previous : null,
    );
  }

  function handleClassChange(nextClass: string) {
    setCharacterClass(nextClass);
    const nextClassOption = options.classes.find(
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

  function handleMethodChange(nextMethod: AbilityScoreMethod) {
    setMethod(nextMethod);
    setRolled(false);
    setFormError(null);
    if (nextMethod === "standard_array") {
      setStandardPicks({});
      setStats({ ...DEFAULT_STATS });
    } else if (nextMethod === "point_buy") {
      setStats((previous) => clampStats(previous, pointBuyMin, pointBuyMax));
    } else if (nextMethod === "roll_4d6") {
      setStats({ ...DEFAULT_STATS });
    }
  }

  async function handleRoll() {
    setRolling(true);
    setFormError(null);
    try {
      const result = await api.rollAbilityScores();
      setStats({ ...result.scores });
      setRolled(true);
    } catch (rollError) {
      setFormError(
        rollError instanceof ApiError
          ? rollError.message
          : "Не удалось бросить кубики",
      );
    } finally {
      setRolling(false);
    }
  }

  function setScore(ability: AbilityKey, value: number) {
    setStats((previous) => ({ ...previous, [ability]: value }));
  }

  function validateScores(): string | null {
    if (method === null) {
      return "Выберите способ генерации характеристик";
    }

    if (method === "manual" || method === "roll_4d6") {
      if (method === "roll_4d6" && !rolled) {
        return "Нажмите «Бросить», чтобы сгенерировать характеристики";
      }
      const { min, max } = options.ability_generation.score_range;
      for (const ability of ABILITIES) {
        const score = stats[ability];
        if (!Number.isInteger(score) || score < min || score > max) {
          return `Характеристики должны быть целыми числами от ${min} до ${max}`;
        }
      }
      return null;
    }

    if (method === "standard_array") {
      const current: number[] = [];
      for (const ability of ABILITIES) {
        const value = standardPicks[ability];
        if (value === undefined) {
          return "Распределите все значения стандартного массива";
        }
        current.push(value);
      }
      if (sortedKey(current) !== sortedKey(standardValues)) {
        return "Назначьте стандартный массив без повторов";
      }
      return null;
    }

    for (const ability of ABILITIES) {
      const score = stats[ability];
      if (
        !Number.isInteger(score) ||
        score < pointBuyMin ||
        score > pointBuyMax
      ) {
        return `При покупке очков характеристики должны быть от ${pointBuyMin} до ${pointBuyMax}`;
      }
    }
    if (pointBuyLeft < 0) {
      return `Перерасход очков характеристик: ${-pointBuyLeft}`;
    }
    return null;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    if (method === null) {
      setFormError("Выберите способ генерации характеристик");
      return;
    }
    if (!name.trim()) {
      setFormError("Укажите имя персонажа");
      return;
    }
    if (
      !Number.isInteger(level) ||
      level < options.level.min ||
      level > options.level.max
    ) {
      setFormError(
        `Уровень должен быть от ${options.level.min} до ${options.level.max}`,
      );
      return;
    }
    const scoreError = validateScores();
    if (scoreError) {
      setFormError(scoreError);
      return;
    }
    const bonusError = validateBackgroundBonus();
    const allocation = bonusAllocation();
    if (bonusError || !allocation) {
      setFormError(bonusError ?? "Выберите бонусы характеристик от предыстории");
      return;
    }

    const baseStatsForSubmit =
      method === "standard_array" ? standardPickedStats(standardPicks) : stats;

    onSubmit({
      name: name.trim(),
      level,
      species,
      character_class: characterClass,
      background,
      ability_score_method: method,
      background_ability_bonus: allocation,
      ...statsWithBonus(allocation, baseStatsForSubmit),
      notes: notes.trim() ? notes.trim() : null,
      data: { skill_proficiencies: selectedSkills },
    });
  }

  const message = formError ?? error;
  const allocation = bonusAllocation();
  const baseStats =
    method === "standard_array" ? standardPickedStats(standardPicks) : stats;
  const totalStats = statsWithBonus(allocation, baseStats);
  const scoreMin =
    method === "point_buy"
      ? pointBuyMin
      : options.ability_generation.score_range.min;
  const scoreMax =
    method === "point_buy"
      ? pointBuyMax
      : options.ability_generation.score_range.max;

  return (
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
                {speciesOptionLabel(item)}
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
            onChange={(event) => handleBackgroundChange(event.target.value)}
          >
            {options.backgrounds.map((item) => (
              <option key={item.name} value={item.name}>
                {item.name}: {item.skills.join(", ")}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="form-grid">
        <label className="field">
          <span>Уровень</span>
          <input
            type="number"
            min={options.level.min}
            max={options.level.max}
            value={level}
            onChange={(event) => setLevel(Number(event.target.value))}
          />
        </label>

        <label className="field">
          <span>Генерация характеристик</span>
          <select
            value={method ?? ""}
            onChange={(event) =>
              handleMethodChange(event.target.value as AbilityScoreMethod)
            }
          >
            <option value="" disabled>
              Выберите способ
            </option>
            {options.ability_generation.methods.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <fieldset className="fieldset">
        <legend>Бонус от предыстории</legend>
        <p className="muted small">
          {background}: {backgroundAbilityScores.map(abilityLabel).join(", ")}
        </p>
        <div className="ability-inputs">
          <label className="field compact-field">
            <span>Распределение</span>
            <select
              value={bonusMode}
              onChange={(event) =>
                setBonusMode(event.target.value as BackgroundBonusMode)
              }
            >
              {bonusModes.map((mode) => (
                <option key={mode.key} value={mode.key}>
                  {mode.label}
                </option>
              ))}
            </select>
          </label>
          {bonusMode === "two_one" && (
            <>
              <label className="field compact-field">
                <span>Куда +2</span>
                <select
                  value={bonusPlusTwo ?? ""}
                  onChange={(event) => {
                    const next = event.target.value;
                    setBonusPlusTwo(next === "" ? null : (next as AbilityKey));
                    if (next !== "" && next === bonusPlusOne) {
                      setBonusPlusOne(null);
                    }
                  }}
                >
                  <option value="" disabled>
                    —
                  </option>
                  {backgroundAbilityScores.map((ability) => (
                    <option key={ability} value={ability}>
                      {abilityLabel(ability)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field compact-field">
                <span>Куда +1</span>
                <select
                  value={bonusPlusOne ?? ""}
                  onChange={(event) => {
                    const next = event.target.value;
                    setBonusPlusOne(next === "" ? null : (next as AbilityKey));
                  }}
                >
                  <option value="" disabled>
                    —
                  </option>
                  {backgroundAbilityScores
                    .filter((ability) => ability !== bonusPlusTwo)
                    .map((ability) => (
                      <option key={ability} value={ability}>
                        {abilityLabel(ability)}
                      </option>
                    ))}
                </select>
              </label>
            </>
          )}
        </div>
        {bonusMode === "one_one_one" && (
          <p className="muted small">
            Каждая из трёх характеристик получает +1.
          </p>
        )}
        {!allocation && (
          <p className="muted small">
            Выберите +2 и +1 среди характеристик предыстории.
          </p>
        )}
      </fieldset>

      <fieldset className="fieldset">
        <legend>Характеристики</legend>
        <div className="score-grid">
          {ABILITIES.map((ability) => (
            <div key={ability} className="score-cell">
              <span>{abilityLabel(ability)}:</span>
              <strong>{totalStats[ability]}</strong>
            </div>
          ))}
        </div>
        {method === null ? (
          <p className="muted small">
            Выберите способ генерации характеристик, чтобы задать значения.
          </p>
        ) : (
          <>
          {method === "standard_array" ? (
            <>
              <div className="ability-inputs">
                {ABILITIES.map((ability) => (
                  <div key={ability} className="field compact-field">
                    <span>{abilityLabel(ability)}</span>
                    <strong>{standardPicks[ability] ?? "—"}</strong>
                  </div>
                ))}
              </div>
              {currentStandardValue === null ? (
                <p className="muted small">
                  Все значения распределены. Нажмите «Сбросить», чтобы начать
                  заново.
                </p>
              ) : (
                <>
                  <p>
                    Отдайте значение <strong>{currentStandardValue}</strong>{" "}
                    характеристике:
                  </p>
                  <div className="button-row">
                    {unassignedStandardAbilities.map((ability) => (
                      <button
                        key={ability}
                        className="button ghost"
                        type="button"
                        onClick={() => assignStandardValue(ability)}
                      >
                        {abilityLabel(ability)}
                      </button>
                    ))}
                  </div>
                </>
              )}
              <div className="button-row">
                <button
                  className="button ghost"
                  type="button"
                  onClick={resetStandardArray}
                  disabled={standardPickedCount === 0}
                >
                  Сбросить
                </button>
              </div>
              {currentStandardValue !== null && (
                <p className="muted small">
                  Осталось значений:{" "}
                  {standardValues.slice(standardPickedCount).join(", ") || "—"}
                </p>
              )}
            </>
          ) : method === "point_buy" ? (
            <div className="ability-sliders">
              {ABILITIES.map((ability) => (
                <label key={ability} className="field compact-field slider-field">
                  <span>
                    {abilityLabel(ability)}: <strong>{stats[ability]}</strong>
                  </span>
                  <input
                    type="range"
                    min={pointBuyMin}
                    max={pointBuyMax}
                    step={1}
                    value={stats[ability]}
                    onChange={(event) =>
                      handlePointBuyChange(ability, Number(event.target.value))
                    }
                  />
                </label>
              ))}
            </div>
          ) : method === "roll_4d6" ? (
            <div className="ability-inputs">
              {ABILITIES.map((ability) => (
                <label key={ability} className="field compact-field">
                  <span>{abilityLabel(ability)}</span>
                  <input
                    type="number"
                    min={scoreMin}
                    max={scoreMax}
                    value={rolled ? stats[ability] : ""}
                    placeholder="—"
                    readOnly
                  />
                </label>
              ))}
            </div>
          ) : (
            <div className="ability-inputs">
              {ABILITIES.map((ability) => (
                <label key={ability} className="field compact-field">
                  <span>{abilityLabel(ability)}</span>
                  <input
                    type="number"
                    min={scoreMin}
                    max={scoreMax}
                    value={stats[ability]}
                    onChange={(event) =>
                      setScore(ability, Number(event.target.value))
                    }
                  />
                </label>
              ))}
            </div>
          )}
          {method === "point_buy" && (
            <p
              className={
                pointsFlash || pointBuyLeft < 0
                  ? "point-buy-left flash"
                  : "point-buy-left muted small"
              }
              aria-live="polite"
            >
              Осталось очков: {pointBuyLeft} из {pointBuyBudget}
            </p>
          )}
          {method === "roll_4d6" && (
            <>
              <div className="button-row">
                <button
                  className="button"
                  type="button"
                  onClick={() => void handleRoll()}
                  disabled={rolling || submitting}
                >
                  {rolling ? "Бросаем..." : "Бросить"}
                </button>
              </div>
              <p className="muted small">
                Бросьте {rollDice.count}d{rollDice.sides} для каждой
                характеристики; худший результат отбрасывается.
              </p>
            </>
          )}
          </>
        )}
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
                className={isBackground ? "check background" : "check"}
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

      {message && <p className="alert error">{message}</p>}

      <div className="button-row">
        <button
          className="button primary"
          type="submit"
          disabled={
            submitting ||
            method === null ||
            (method === "point_buy" && pointBuyLeft < 0) ||
            (method === "roll_4d6" && !rolled)
          }
        >
          {submitting ? pendingLabel : submitLabel}
        </button>
        {onCancel && (
          <button className="button ghost" type="button" onClick={onCancel}>
            Отмена
          </button>
        )}
      </div>
    </form>
  );
}
