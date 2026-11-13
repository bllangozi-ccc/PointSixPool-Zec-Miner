namespace Point6Miner.Core;

public sealed record ResourceSample(DateTimeOffset At, double? CpuPercent, double? RamAvailableGiB,
    double? DiskFreeGiB, double? CpuTemperatureC, double? GpuTemperatureC,
    double? GpuPercent, double? GpuFreeVramGiB, bool? ThermalThrottling, string Source);

public sealed record AdditionRequirements(string Hardware, double ProjectedCpuPercent,
    double RequiredRamGiB, double RequiredDiskGiB, double RequiredVramGiB,
    double? VerifiedManufacturerTemperatureLimitC, bool BackendAccepted,
    bool PowerBudgetMeasured, bool StableBaselineMeasured, bool UserConsented);

public sealed record Recommendation(bool EligibleForManualReview, string Reason);

public static class AdditionalCoin
{
    public static Recommendation Evaluate(PoolProfile candidate, ResourceSample current,
        AdditionRequirements requirements, DateTimeOffset now)
    {
        Recommendation No(string reason) => new(false, reason);
        if (!candidate.Qualified || !candidate.SettlementQualified || candidate.Endpoint == null)
            return No("No qualified additional PointSix pool is available.");
        if (!requirements.BackendAccepted || candidate.Hardware != requirements.Hardware)
            return No("Compatible signed backend and hardware acceptance are required.");
        if (requirements.Hardware is not ("CPU" or "GPU"))
            return No("Additional workload sensors are not qualified for this hardware.");
        if (current.Source != "validated-local-sensors" || current.At > now || now - current.At > TimeSpan.FromSeconds(10))
            return No("Fresh validated machine readings are required.");
        if (!requirements.StableBaselineMeasured || !requirements.PowerBudgetMeasured)
            return No("A measured stable baseline and wall-power budget are required.");
        double? temperature = requirements.Hardware == "GPU" ? current.GpuTemperatureC : current.CpuTemperatureC;
        if (temperature == null || current.ThermalThrottling != false || requirements.VerifiedManufacturerTemperatureLimitC == null)
            return No("Temperature, throttling and the hardware manufacturer's limit must be available.");
        if (!double.IsFinite(requirements.VerifiedManufacturerTemperatureLimitC.Value)
            || requirements.VerifiedManufacturerTemperatureLimitC <= 10 || requirements.VerifiedManufacturerTemperatureLimitC > 150)
            return No("The verified manufacturer's temperature limit is invalid.");
        if (!double.IsFinite(temperature.Value) || temperature < 0 || temperature > requirements.VerifiedManufacturerTemperatureLimitC - 10)
            return No("Measured temperature does not have the required margin.");
        if (current.CpuPercent == null || !double.IsFinite(current.CpuPercent.Value) || current.CpuPercent < 0
            || current.CpuPercent + requirements.ProjectedCpuPercent > 50)
            return No("CPU headroom is insufficient or unknown.");
        if (current.RamAvailableGiB == null || current.DiskFreeGiB == null
            || !double.IsFinite(current.RamAvailableGiB.Value) || !double.IsFinite(current.DiskFreeGiB.Value)
            || current.RamAvailableGiB < requirements.RequiredRamGiB + 4 || current.DiskFreeGiB < requirements.RequiredDiskGiB + 20)
            return No("Memory/disk headroom is insufficient or unknown.");
        if (requirements.Hardware == "GPU" && (current.GpuPercent == null || current.GpuFreeVramGiB == null
            || !double.IsFinite(current.GpuPercent.Value) || !double.IsFinite(current.GpuFreeVramGiB.Value)
            || current.GpuPercent < 0 || current.GpuPercent > 50 || current.GpuFreeVramGiB < requirements.RequiredVramGiB + 1))
            return No("GPU load and VRAM headroom are insufficient or unknown.");
        if (new[] { requirements.ProjectedCpuPercent, requirements.RequiredRamGiB,
            requirements.RequiredDiskGiB, requirements.RequiredVramGiB }.Any(v => !double.IsFinite(v) || v < 0))
            return No("Resource requirements are invalid.");
        if (!requirements.UserConsented) return No("Confirm this additional workload before any action.");
        return new(true, "Candidate meets the measured checks for manual review. This prototype cannot start miners.");
    }
}
