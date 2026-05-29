class TrainingGenerator:
    """Generates training loop and main block."""

    def __init__(self, generator):
        self.g = generator

    def generate(self):
        optimizer = next((n for n in self.g.nodes if n["type"] == "optimizer"), None)
        output_node = next((n for n in self.g.nodes if n["type"] == "output"), None)

        lines = []

        if optimizer:
            lines.extend(self._optimizer_config(optimizer))
            lines.append("")
            lines.extend(self._train_function(optimizer))
        else:
            lines.append("# No optimizer configured — inference only")

        lines.append("")
        lines.append('if __name__ == "__main__":')
        lines.append("    train_loader, test_loader = load_data()")
        lines.append("    model = SketchNetModel()")

        if optimizer:
            lines.append("    train_losses, val_losses = train_model(")
            lines.append("        model, train_loader, test_loader, optimizer, loss_fn")
            lines.append("    )")
            lines.append("")
            lines.append("    # Evaluation")
            lines.append("    model.eval()")
            lines.append("    correct = 0")
            lines.append("    total = 0")
            lines.append("    with torch.no_grad():")
            lines.append("        for batch_x, batch_y in test_loader:")
            lines.append("            pred = model(batch_x)")
            lines.append("            _, predicted = torch.max(pred, 1)")
            lines.append("            total += batch_y.size(0)")
            lines.append("            correct += (predicted == batch_y).sum().item()")
            lines.append("    print(f'Accuracy: {100 * correct / total:.2f}%')")

        return lines

    def _optimizer_config(self, opt):
        loss_map = {
            "cross_entropy": "nn.CrossEntropyLoss()",
            "mse": "nn.MSELoss()",
            "bce": "nn.BCELoss()",
            "nll": "nn.NLLLoss()",
            "l1": "nn.L1Loss()",
            "huber": "nn.HuberLoss()",
        }
        loss_fn = loss_map.get(opt.get("lossType"), "nn.CrossEntropyLoss()")
        lines = [f"loss_fn = {loss_fn}"]

        opt_type = opt.get("optimizerType", "adam")
        lr = opt.get("learningRate", 0.001)

        if opt_type == "adam":
            b1 = opt.get("adamBeta1", 0.9)
            b2 = opt.get("adamBeta2", 0.999)
            eps = opt.get("adamEpsilon", 1e-8)
            lines.append(
                f"optimizer = optim.Adam(model.parameters(), lr={lr}, betas=({b1}, {b2}), eps={eps})"
            )
        elif opt_type == "adamw":
            b1 = opt.get("adamBeta1", 0.9)
            b2 = opt.get("adamBeta2", 0.999)
            eps = opt.get("adamEpsilon", 1e-8)
            wd = opt.get("weightDecay", 0)
            lines.append(
                f"optimizer = optim.AdamW(model.parameters(), lr={lr}, betas=({b1}, {b2}), eps={eps}, weight_decay={wd})"
            )
        elif opt_type == "sgd":
            mom = opt.get("sgdMomentum", 0.9)
            wd = opt.get("weightDecay", 0)
            nesterov = ", nesterov=True" if opt.get("nesterov") else ""
            lines.append(
                f"optimizer = optim.SGD(model.parameters(), lr={lr}, momentum={mom}, weight_decay={wd}{nesterov})"
            )

        return lines

    def _train_function(self, opt):
        epochs = opt.get("epochs", 10)
        grad_clip = opt.get("gradientClip")
        early_stop = opt.get("earlyStopping", False)
        patience = opt.get("earlyStoppingPatience", 10)

        lines = []
        lines.append(
            "def train_model(model, train_loader, val_loader, optimizer, loss_fn):"
        )
        lines.append("    train_losses = []")
        lines.append("    val_losses = []")

        if early_stop:
            lines.append("    best_val_loss = float('inf')")
            lines.append("    patience_counter = 0")
            lines.append("    best_model_state = None")

        lines.append(f"    for epoch in range({epochs}):")
        lines.append("        model.train()")
        lines.append("        total_loss = 0")
        lines.append("        for batch_x, batch_y in train_loader:")
        lines.append("            optimizer.zero_grad()")
        lines.append("            pred = model(batch_x)")
        lines.append("            loss = loss_fn(pred, batch_y)")
        lines.append("            loss.backward()")

        if grad_clip:
            lines.append(
                f"            torch.nn.utils.clip_grad_norm_(model.parameters(), {grad_clip})"
            )

        lines.append("            optimizer.step()")
        lines.append("            total_loss += loss.item()")
        lines.append("        avg_loss = total_loss / len(train_loader)")
        lines.append("        train_losses.append(avg_loss)")
        lines.append("")
        lines.append("        model.eval()")
        lines.append("        val_loss = 0")
        lines.append("        with torch.no_grad():")
        lines.append("            for batch_x, batch_y in val_loader:")
        lines.append("                pred = model(batch_x)")
        lines.append("                loss = loss_fn(pred, batch_y)")
        lines.append("                val_loss += loss.item()")
        lines.append("        avg_val = val_loss / len(val_loader)")
        lines.append("        val_losses.append(avg_val)")
        lines.append(
            f"        print(f'Epoch {{epoch+1}}/{epochs} - Train: {{avg_loss:.4f}} - Val: {{avg_val:.4f}}')"
        )

        if early_stop:
            lines.append("")
            lines.append("        if avg_val < best_val_loss:")
            lines.append("            best_val_loss = avg_val")
            lines.append("            patience_counter = 0")
            lines.append(
                "            best_model_state = {k: v.clone() for k, v in model.state_dict().items()}"
            )
            lines.append("        else:")
            lines.append("            patience_counter += 1")
            lines.append(f"            if patience_counter >= {patience}:")
            lines.append(
                f"                print(f'Early stopping at epoch {{epoch+1}}')"
            )
            lines.append("                model.load_state_dict(best_model_state)")
            lines.append("                break")

        lines.append("    return train_losses, val_losses")
        return lines
