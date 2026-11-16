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
}

export interface SkillOption {
  name: string;
  ability: AbilityKey;
}

export interface CharacterOptions {
  abilities: AbilityOption[];
  species: SpeciesOption[];
  classes: ClassOption[];
  backgrounds: BackgroundOption[];
  skills: SkillOption[];
  level: { min: number; max: number };
  limits: { max_message_length: number };
}

export interface CharacterData {
  ability_modifiers?: Record<AbilityKey, number>;
  proficiency_bonus?: number;
  initiative?: number;
  passive_perception?: number;
  skill_proficiencies?: string[];
  skill_modifiers?: Record<string, number>;
  saving_throws?: Record<AbilityKey, number>;
  species_speed?: number;
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

export interface CheckRequest {
  ability: AbilityKey;
  skill: string | null;
  dc: number;
}

export interface MessageRequest {
  content: string;
  client_message_id: string;
  check: CheckRequest | null;
}

export interface CharacterCreatePayload {
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
  notes: string | null;
  data: { skill_proficiencies: string[] };
}
