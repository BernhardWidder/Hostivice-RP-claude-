using UnrealBuildTool;

public class HostiviceZaCarouTarget : TargetRules
{
	public HostiviceZaCarouTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_5;
		ExtraModuleNames.AddRange(new string[]
		{
			"HostiviceCore",
			"HostiviceVehicles",
			"HostiviceAI",
			"HostiviceWorld",
			"HostiviceMissions"
		});
	}
}
