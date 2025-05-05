from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import get_peft_model, LoraConfig, TaskType
from datasets import Dataset
import torch
import json

# Load dataset
def load_jsonl(path):
    with open(path, "r") as f:
        lines = [json.loads(line.strip()) for line in f]
    return Dataset.from_list(lines)

dataset = load_jsonl("splunk_query_data.json")

# Model and tokenizer
model_name = "bigcode/starcoder2-7b"
tokenizer = AutoTokenizer.from_pretrained(model_name, padding_side="right")
tokenizer.pad_token = tokenizer.eos_token  # Avoid padding issues

model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32)

# Apply LoRA
lora_config = LoraConfig(
    r=8,
    lora_alpha=32,
    target_modules=["c_proj", "q_proj", "v_proj"],  # works well for StarCoder2
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM
)
model = get_peft_model(model, lora_config)

# Preprocessing
def preprocess(example):
    prompt = example["input"]
    response = example["output"]
    full_text = f"### User Query:\n{prompt}\n### SPL + Fields:\n{response}"
    tokenized = tokenizer(full_text, padding="max_length", truncation=True, max_length=512)
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

tokenized_dataset = dataset.map(preprocess)

# Data collator
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# Training arguments
training_args = TrainingArguments(
    output_dir="./starcoder2-lora-splunk",
    per_device_train_batch_size=1,
    num_train_epochs=3,
    learning_rate=2e-5,
    logging_dir="./logs",
    save_strategy="epoch",
    evaluation_strategy="no",
    save_total_limit=2,
    fp16=False,  # Enable if using CUDA
    bf16=False,
    remove_unused_columns=False,
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

# Train
trainer.train()
model.save_pretrained("./starcoder2-lora-splunk")
tokenizer.save_pretrained("./starcoder2-lora-splunk")
