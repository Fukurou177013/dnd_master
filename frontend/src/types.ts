export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface AbilityOption {
  key: AbilityKey;
  label: string;
}

export type AbilityKey =
  | "strength"
  | "dexterity"
  | "constitution"
  | "intelligence"
  | "wisdom"
  | "charisma";

export interface SpeciesOption {
  name: string;
  speed: number;
  darkvision: number;
}

export interface ClassOption {
  name: string;
  hit_die: number;
  saving_throws: AbilityKey[];
  skill_choices: string[];
  skill_count: number;
}

export interface BackgroundOption {
  name: string;
  skills: string[];
  ability_scores: AbilityKey[];
}

export type BackgroundBonusMode = "two_one" | "one_one_one";

export interface BackgroundBonusModeOption {
  key: BackgroundBonusMode;
  label: string;
  values: number[];
}

export interface BackgroundAbilityBonus {
  max_score: number;
  modes: BackgroundBonusModeOption[];
}

export interface SkillOption {
  name: string;
  ability: AbilityKey;
}

export type AbilityScoreMethod =
  | "manual"
  | "standard_array"
  | "point_buy"
  | "roll_4d6";

export interface AbilityGenerationMethod {
  key: AbilityScoreMethod;
  label: string;
  values?: number[];
  budget?: number;
  min?: number;
  max?: number;
  costs?: Record<string, number>;
  dice?: { count: number; sides: number; drop_lowest: number };
}

export interface AbilityGeneration {
  score_range: { min: number; max: number };
  methods: AbilityGenerationMethod[];
}

export interface CharacterOptions {
  abilities: AbilityOption[];
  species: SpeciesOption[];
  classes: ClassOption[];
  backgrounds: BackgroundOption[];
  skills: SkillOption[];
  level: { min: number; max: number };
  background_ability_bonus: BackgroundAbilityBonus;
  ability_generation: AbilityGeneration;
  limits: { max_message_length: number };
}

export interface CharacterData {
  ability_score_method?: AbilityScoreMethod;
  background_ability_bonus?: Partial<Record<AbilityKey, number>>;
  ability_modifiers?: Record<AbilityKey, number>;
  proficiency_bonus?: number;
  initiative?: number;
  passive_perception?: number;
  skill_proficiencies?: string[];
  skill_modifiers?: Record<string, number>;
  saving_throws?: Record<AbilityKey, number>;
  species_speed?: number;
  darkvision?: number;
  [key: string]: unknown;
}

export interface Character {
  id: string;
  name: string;
  level: number;
  species: string;
  character_class: string;
  background: string;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  max_hp: number;
  current_hp: number;
  armor_class: number;
  speed: number;
  notes: string | null;
  data: CharacterData;
  created_at: string;
  updated_at: string;
}

export interface CampaignSummary {
  facts: string[];
  goals: string[];
  npcs: string[];
  locations: string[];
  open_threads: string[];
}

export interface Campaign {
  id: string;
  name: string;
  character_id: string;
  premise: string | null;
  summary: CampaignSummary;
  created_at: string;
  updated_at: string;
}

export interface Roll {
  kind: "ability" | "skill";
  ability: AbilityKey;
  ability_label: string;
  skill: string | null;
  d20: number;
  modifier: number;
  proficient: boolean;
  dc: number;
  total: number;
  success: boolean;
}

export interface Source {
  id: string;
  source: string;
  section: string;
  title: string;
  license: string;
  excerpt: string;
}

export interface CampaignMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sequence: number;
  roll: Roll | null;
  sources: Source[];
  created_at: string;
}

export interface CampaignExchange {
  user_message: CampaignMessage;
  assistant_message: CampaignMessage;
  memory_update_scheduled: boolean;
}

export interface MessageRequest {
  content: string;
  client_message_id: string;
}

export interface AbilityScoreRoll {
  method: AbilityScoreMethod;
  scores: Record<AbilityKey, number>;
}

export interface CharacterCreatePayload {
  name: string;
  level: number;
  species: string;
  character_class: string;
  background: string;
  ability_score_method: AbilityScoreMethod;
  background_ability_bonus: Partial<Record<AbilityKey, number>>;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  notes: string | null;
  data: { skill_proficiencies: string[] };
}

export interface CharacterUpdatePayload {
  name?: string;
  level?: number;
  species?: string;
  character_class?: string;
  background?: string;
  ability_score_method?: AbilityScoreMethod;
  background_ability_bonus?: Partial<Record<AbilityKey, number>>;
  strength?: number;
  dexterity?: number;
  constitution?: number;
  intelligence?: number;
  wisdom?: number;
  charisma?: number;
  current_hp?: number;
  notes?: string | null;
  data?: { skill_proficiencies: string[] };
}
