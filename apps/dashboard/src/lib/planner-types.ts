export type ArmOption = {
  arm_id: string;
  file_name: string;
  provider: string | null;
  model: string | null;
  backend_model: string | null;
  job_dir_name: string | null;
};

export type TaskSetOption = {
  id: string;
  file_name: string;
  task_count: number;
  sample_tasks: string[];
};
