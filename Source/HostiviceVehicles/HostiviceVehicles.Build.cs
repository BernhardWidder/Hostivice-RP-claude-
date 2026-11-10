using UnrealBuildTool;

// Vozový park: Chaos Vehicles, palivo, poškození, nastupování.
public class HostiviceVehicles : ModuleRules
{
	public HostiviceVehicles(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "HostiviceCore", "ChaosVehicles", "PhysicsCore", "InputCore", "EnhancedInput"
		});
	}
}
