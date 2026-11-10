using UnrealBuildTool;

// Sdílený základ: rozhraní, logování, společné typy.
public class HostiviceCore : ModuleRules
{
	public HostiviceCore(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine"
		});
	}
}
