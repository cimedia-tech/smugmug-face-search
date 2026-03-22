export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]

export type Database = {
  public: {
    Tables: {
      oauth_pending: {
        Row: {
          request_token:        string
          request_token_secret: string
          expires_at:           string
        }
        Insert: {
          request_token:        string
          request_token_secret: string
          expires_at?:          string
        }
        Update: {
          request_token?:        string
          request_token_secret?: string
          expires_at?:           string
        }
        Relationships: []
      }
      oauth_tokens: {
        Row: {
          id:                  number
          access_token:        string
          access_token_secret: string
          smugmug_user:        string
          saved_at:            string
        }
        Insert: {
          id:                  number
          access_token:        string
          access_token_secret: string
          smugmug_user:        string
          saved_at?:           string
        }
        Update: {
          access_token?:        string
          access_token_secret?: string
          smugmug_user?:        string
          saved_at?:            string
        }
        Relationships: []
      }
      indexing_jobs: {
        Row: {
          id:             number
          status:         string
          folder_path:    string | null
          album_keys:     string[] | null
          total_images:   number
          indexed_count:  number
          last_image_key: string | null
          started_at:     string
          updated_at:     string
          error:          string | null
        }
        Insert: {
          status?:         string
          folder_path?:    string | null
          album_keys?:     string[] | null
          total_images?:   number
          indexed_count?:  number
          last_image_key?: string | null
          error?:          string | null
        }
        Update: {
          status?:         string
          folder_path?:    string | null
          album_keys?:     string[] | null
          total_images?:   number
          indexed_count?:  number
          last_image_key?: string | null
          updated_at?:     string
          error?:          string | null
        }
        Relationships: []
      }
      person_clusters: {
        Row: {
          id:             number
          name:           string | null
          sample_face_id: number | null
          created_at:     string
        }
        Insert: {
          name?:           string | null
          sample_face_id?: number | null
        }
        Update: {
          name?:           string | null
          sample_face_id?: number | null
        }
        Relationships: []
      }
      face_index: {
        Row: {
          id:                   number
          smugmug_image_key:    string
          album_key:            string | null
          image_url:            string | null
          thumbnail_url:        string | null
          face_embedding:       string | null
          face_index_in_photo:  number
          bbox_x:               number | null
          bbox_y:               number | null
          bbox_w:               number | null
          bbox_h:               number | null
          face_crop_url:        string | null
          cluster_id:           number | null
          indexed_at:           string
        }
        Insert: {
          smugmug_image_key:    string
          album_key?:           string | null
          image_url?:           string | null
          thumbnail_url?:       string | null
          face_embedding?:      unknown
          face_index_in_photo?: number
          bbox_x?:              number | null
          bbox_y?:              number | null
          bbox_w?:              number | null
          bbox_h?:              number | null
          face_crop_url?:       string | null
          cluster_id?:          number | null
        }
        Update: {
          album_key?:           string | null
          image_url?:           string | null
          thumbnail_url?:       string | null
          face_embedding?:      unknown
          face_index_in_photo?: number
          bbox_x?:              number | null
          bbox_y?:              number | null
          bbox_w?:              number | null
          bbox_h?:              number | null
          face_crop_url?:       string | null
          cluster_id?:          number | null
        }
        Relationships: [
          {
            foreignKeyName: "face_index_cluster_id_fkey"
            columns: ["cluster_id"]
            referencedRelation: "person_clusters"
            referencedColumns: ["id"]
          }
        ]
      }
      search_jobs: {
        Row: {
          id:         number
          status:     string
          image_url:  string
          top_k:      number
          results:    Json | null
          error:      string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          image_url:  string
          status?:    string
          top_k?:     number
          results?:   Json | null
          error?:     string | null
        }
        Update: {
          status?:     string
          top_k?:      number
          results?:    Json | null
          error?:      string | null
          updated_at?: string
        }
        Relationships: []
      }
    }
    Views: {
      person_clusters_with_counts: {
        Row: {
          id:              number | null
          name:            string | null
          sample_face_id:  number | null
          sample_face_url: string | null
          photo_count:     number | null
        }
        Relationships: []
      }
    }
    Functions: Record<string, never>
    Enums: Record<string, never>
    CompositeTypes: Record<string, never>
  }
}
