export interface ColourEntry {
  value: string;
  count: number;
}

export interface ExampleImage {
  image_url: string;
  username: string;
  likes_count: number;
  comments_count: number;
  reposts_count: number;
  follower_count: number;
  engagement_score: number;
}

export interface GarmentTrend {
  garment_type: string;
  post_count: number;
  unique_influencer_count: number;
  top_colours: ColourEntry[];
  top_fits: ColourEntry[];
  top_style_features: ColourEntry[];
  example_images: ExampleImage[];
}

export interface TrendsSummary {
  total_posts_analysed: number;
  total_items_analysed: number;
  garment_types: GarmentTrend[];
}

export interface VelocityData {
  direction: "up" | "down" | "flat" | "new";
  pct: number;
  thisWeek: number;
  lastWeek: number;
}

export interface WeeklyColour {
  colour: string;
  count: number;
  hex: string;
}

export interface OutfitPair {
  garment_a: string;
  garment_b: string;
  count: number;
}
