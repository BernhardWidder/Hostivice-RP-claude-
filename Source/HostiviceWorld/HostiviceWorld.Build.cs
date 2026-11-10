using UnrealBuildTool;

// Svět: cyklus dne, počasí, streamování interiérů, obchody.
public class HostiviceWorld : ModuleRules
{
	public HostiviceWorld(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "HostiviceCore"
		});
	}
}
