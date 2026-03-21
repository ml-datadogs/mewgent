import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { StatDistribution } from '@/components/StatDistribution';
import { ClassFit } from '@/components/ClassFit';
import { TopThreeList } from '@/components/TopThreeList';
import { AvgRadar } from '@/components/AvgRadar';
import { BreedingPanel } from '@/components/BreedingPanel';
import type { RosterEntry, CollarDef } from '@/types';

interface OverviewProps {
  roster: RosterEntry[];
  collars: CollarDef[];
  llmAvailable: boolean;
  bridgeConnected: boolean;
  hideBreedTab?: boolean;
}

const tabVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

export function Overview({
  roster,
  collars,
  llmAvailable,
  bridgeConnected,
  hideBreedTab,
}: OverviewProps) {
  const cats = roster.map((r) => r.cat);

  return (
    <div className="flex flex-col gap-1.5">
      <Tabs defaultValue="stats">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-accent tracking-wider">
            ROSTER OVERVIEW
          </span>
          <div className="flex-1" />
          <TabsList>
            <TabsTrigger value="stats">Stats</TabsTrigger>
            <TabsTrigger value="classes">Classes</TabsTrigger>
            <TabsTrigger value="top3">Top 3</TabsTrigger>
            <TabsTrigger value="avg">Avg</TabsTrigger>
            {!hideBreedTab && <TabsTrigger value="breed">Breed</TabsTrigger>}
          </TabsList>
        </div>

        <Card className="mt-1.5">
          <CardContent className="p-2">
            <AnimatePresence mode="wait">
              <TabsContent value="stats" key="stats" forceMount={undefined}>
                <motion.div
                  variants={tabVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={{ duration: 0.2 }}
                >
                  {cats.length > 0 ? (
                    <StatDistribution cats={cats} />
                  ) : (
                    <EmptyState />
                  )}
                </motion.div>
              </TabsContent>

              <TabsContent value="classes" key="classes" forceMount={undefined}>
                <motion.div
                  variants={tabVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={{ duration: 0.2 }}
                >
                  {cats.length > 0 ? (
                    <ClassFit cats={cats} collars={collars} />
                  ) : (
                    <EmptyState />
                  )}
                </motion.div>
              </TabsContent>

              <TabsContent value="top3" key="top3" forceMount={undefined}>
                <motion.div
                  variants={tabVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={{ duration: 0.2 }}
                >
                  {cats.length > 0 ? (
                    <TopThreeList cats={cats} collars={collars} />
                  ) : (
                    <EmptyState />
                  )}
                </motion.div>
              </TabsContent>

              <TabsContent value="avg" key="avg" forceMount={undefined}>
                <motion.div
                  variants={tabVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={{ duration: 0.2 }}
                >
                  {cats.length > 0 ? (
                    <AvgRadar cats={cats} />
                  ) : (
                    <EmptyState />
                  )}
                </motion.div>
              </TabsContent>

              {!hideBreedTab && (
                <TabsContent value="breed" key="breed" forceMount={undefined}>
                  <motion.div
                    variants={tabVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    transition={{ duration: 0.2 }}
                  >
                    {cats.length >= 2 ? (
                      <BreedingPanel
                        cats={cats}
                        collars={collars}
                        llmAvailable={llmAvailable}
                        bridgeConnected={bridgeConnected}
                      />
                    ) : (
                      <EmptyState />
                    )}
                  </motion.div>
                </TabsContent>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>
      </Tabs>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex items-center justify-center h-[160px] text-text-dim text-xs">
      Save data not loaded yet
    </div>
  );
}
