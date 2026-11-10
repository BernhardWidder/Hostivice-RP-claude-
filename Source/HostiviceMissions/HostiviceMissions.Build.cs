using UnrealBuildTool;

// Mise, frakce a reputace.
public class HostiviceMissions : ModuleRules
{
	public HostiviceMissions(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "HostiviceCore"
		});
	}
}
