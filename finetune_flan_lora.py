from transformers import (
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq
)
from datasets import load_dataset, Dataset
from peft import get_peft_model, LoraConfig, TaskType
import torch
import json

# Load data
def load_jsonl(path):
    with open(path, "r") as f:
        lines = [json.loads(l.strip()) for l in f]
    return Dataset.from_list(lines)

dataset = load_jsonl("splunk_query_data.json")

# Use flan-t5-small for lower memory usage
model_name = "google/flan-t5-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)

def preprocess(example):
    input_text = example["input"]
    output_text = example["output"]
    model_input = tokenizer(input_text, max_length=128, truncation=True, padding="max_length")
    label = tokenizer(output_text, max_length=128, truncation=True, padding="max_length")
    model_input["labels"] = label["input_ids"]
    return model_input

tokenized_data = dataset.map(preprocess)

# Load model and apply LoRA
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
lora_config = LoraConfig(
    r=8,
    lora_alpha=32,
    target_modules=["q", "v"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.SEQ_2_SEQ_LM
)
model = get_peft_model(model, lora_config)

# Use CPU to avoid MPS memory crash
device = torch.device("cpu")
model.to(device)

# Training arguments
training_args = Seq2SeqTrainingArguments(
    output_dir="./flan-lora-splunk",
    per_device_train_batch_size=2,
    learning_rate=2e-4,
    num_train_epochs=3,
    logging_dir="./logs",
    save_total_limit=2,
    save_steps=200,
    fp16=False  # Disable fp16 for CPU/MPS
)

# Trainer
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_data,
    tokenizer=tokenizer,
    data_collator=DataCollatorForSeq2Seq(tokenizer, model=model)
)

# Train and save
trainer.train()
model.save_pretrained("./flan-lora-splunk")
tokenizer.save_pretrained("./flan-lora-splunk")
