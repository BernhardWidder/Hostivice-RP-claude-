using UnrealBuildTool;

// Chodci, provoz a policie (Mass Entity, ZoneGraph, StateTree). Závislosti na Mass modulech přidávat až s prvním kódem.
public class HostiviceAI : ModuleRules
{
	public HostiviceAI(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "HostiviceCore"
		});
	}
}
